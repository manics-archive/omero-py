#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
   Test of the HDF storage for the Tables API.

   Copyright 2009-2014 Glencoe Software, Inc. All rights reserved.
   Use is subject to license terms supplied in LICENSE.txt

"""
from __future__ import division
from __future__ import print_function

from builtins import str
from past.utils import old_div
from builtins import object
import time
import pytest
import omero.columns
import logging
import tables
import threading
import Ice

from mox3 import mox
from omero.rtypes import rint, rstring

from library import TestCase
from omero_ext.path import path

import omero.hdfstorageV2 as storage_module


HdfList = storage_module.HdfList
HdfStorage = storage_module.HdfStorage


logging.basicConfig(level=logging.CRITICAL)


class MockAdapter(object):
    def __init__(self, ic):
        self.ic = ic

    def getCommunicator(self):
        return self.ic


class TestHdfStorage(TestCase):

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.ic = Ice.initialize()
        self.current = Ice.Current()
        self.current.adapter = MockAdapter(self.ic)
        self.lock = threading.RLock()

        for of in list(omero.columns.ObjectFactories.values()):
            of.register(self.ic)

    def cols(self):
        a = omero.columns.LongColumnI('a', 'first', None)
        b = omero.columns.LongColumnI('b', 'first', None)
        c = omero.columns.LongColumnI('c', 'first', None)
        return [a, b, c]

    def init(self, hdf, meta=False):
        if meta:
            m = {"analysisA": 1, "analysisB": "param", "analysisC": 4.1}
        else:
            m = None
        hdf.initialize(self.cols(), m)

    def append(self, hdf, map):
        cols = self.cols()
        for col in cols:
            try:
                col.values = [map[col.name]]
            except KeyError:
                col.values = []
        hdf.append(cols)

    def hdfpath(self):
        tmpdir = self.tmpdir()
        return old_div(path(tmpdir), "test.h5")

    def testInvalidFile(self):
        pytest.raises(
            omero.ApiUsageException, HdfStorage, None, None)
        pytest.raises(
            omero.ApiUsageException, HdfStorage, '', self.lock)
        bad = path(self.tmpdir()) / "doesntexist" / "test.h5"
        pytest.raises(
            omero.ApiUsageException, HdfStorage, bad, self.lock)

    def testValidFile(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        hdf.cleanup()

    def testLocking(self):
        tmp = str(self.hdfpath())
        hdf1 = HdfStorage(tmp, self.lock)
        with pytest.raises(omero.LockTimeout) as exc_info:
            HdfStorage(tmp, self.lock)
        assert exc_info.value.message.startswith('Path already in HdfList: ')
        hdf1.cleanup()
        hdf3 = HdfStorage(tmp, self.lock)
        hdf3.cleanup()

    def testSimpleCreation(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, False)
        hdf.cleanup()

    def testCreationWithMetadata(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, True)
        hdf.cleanup()

    def testAddSingleRow(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, True)
        self.append(hdf, {"a": 1, "b": 2, "c": 3})
        hdf.cleanup()

    def testModifyRow(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, True)
        self.append(hdf, {"a": 1, "b": 2, "c": 3})
        self.append(hdf, {"a": 5, "b": 6, "c": 7})
        data = hdf.readCoordinates(hdf._stamp, [0, 1], self.current)
        assert len(data.columns) == 3
        assert 1 == data.columns[0].values[0]
        assert 5 == data.columns[0].values[1]
        assert 2 == data.columns[1].values[0]
        assert 6 == data.columns[1].values[1]
        assert 3 == data.columns[2].values[0]
        assert 7 == data.columns[2].values[1]

        data.columns[0].values[0] = 100
        data.columns[0].values[1] = 200
        data.columns[1].values[0] = 300
        data.columns[1].values[1] = 400
        hdf.update(hdf._stamp, data)
        hdf.readCoordinates(hdf._stamp, [0, 1], self.current)
        assert len(data.columns) == 3
        assert 100 == data.columns[0].values[0]
        assert 200 == data.columns[0].values[1]
        assert 300 == data.columns[1].values[0]
        assert 400 == data.columns[1].values[1]
        assert 3 == data.columns[2].values[0]
        assert 7 == data.columns[2].values[1]
        hdf.cleanup()

    def testReadTicket1951(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, True)
        self.append(hdf, {"a": 1, "b": 2, "c": 3})
        data = hdf.readCoordinates(hdf._stamp, [0], self.current)
        assert 1 == data.columns[0].values[0]
        assert 2 == data.columns[1].values[0]
        assert 3 == data.columns[2].values[0]
        data = hdf.read(hdf._stamp, [0, 1, 2], 0, 1, self.current)
        assert 1 == data.columns[0].values[0]
        assert 2 == data.columns[1].values[0]
        assert 3 == data.columns[2].values[0]
        hdf.cleanup()

    def testSorting(self):  # Probably shouldn't work
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, True)
        self.append(hdf, {"a": 0, "b": 2, "c": 3})
        self.append(hdf, {"a": 4, "b": 4, "c": 4})
        self.append(hdf, {"a": 0, "b": 1, "c": 0})
        self.append(hdf, {"a": 0, "b": 0, "c": 0})
        self.append(hdf, {"a": 0, "b": 4, "c": 0})
        self.append(hdf, {"a": 0, "b": 0, "c": 0})
        hdf.getWhereList(time.time(), '(a==0)', None, 'b', None, None, None)
        # Doesn't work yet.
        hdf.cleanup()

    def testInitializeInvalidColoumnNames(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)

        with pytest.raises(omero.ApiUsageException) as exc:
            hdf.initialize([omero.columns.LongColumnI('')], None)
        assert exc.value.message.startswith('Column unnamed:')

        with pytest.raises(omero.ApiUsageException) as exc:
            hdf.initialize([omero.columns.LongColumnI('__a')], None)
        assert exc.value.message == 'Reserved column name: __a'

        hdf.initialize([omero.columns.LongColumnI('a')], None)
        hdf.cleanup()

    def testInitializationOnInitializedFileFails(self):
        p = self.hdfpath()
        hdf = HdfStorage(p, self.lock)
        self.init(hdf, True)
        hdf.cleanup()
        hdf = HdfStorage(p, self.lock)
        try:
            self.init(hdf, True)
            assert False
        except omero.ApiUsageException:
            pass
        hdf.cleanup()

    """
    Hard fails disabled. See #2067
    def testAddColumn(self):
        assert False, "NYI"

    def testMergeFiles(self):
        assert False, "NYI"

    def testVersion(self):
        assert False, "NYI"
    """

    def testHandlesExistingDirectory(self):
        t = path(self.tmpdir())
        h = old_div(t, "test.h5")
        assert t.exists()
        hdf = HdfStorage(h, self.lock)
        hdf.cleanup()

    @pytest.mark.xfail
    @pytest.mark.broken(reason = "TODO after python3 migration")
    def testGetSetMetaMap(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        self.init(hdf, False)

        hdf.add_meta_map({'a': rint(1)})
        m1 = hdf.get_meta_map()
        assert len(m1) == 3
        assert m1['__initialized'].val > 0
        assert m1['__version'] == rstring('2')
        assert m1['a'] == rint(1)

        with pytest.raises(omero.ApiUsageException) as exc:
            hdf.add_meta_map({'b': rint(1), '__c': rint(2)})
        assert exc.value.message == 'Reserved attribute name: __c'
        assert hdf.get_meta_map() == m1

        with pytest.raises(omero.ValidationException) as exc:
            hdf.add_meta_map({'d': rint(None)})
        assert exc.value.serverStackTrace.startswith('Unsupported type:')
        assert hdf.get_meta_map() == m1

        hdf.add_meta_map({}, replace=True)
        m2 = hdf.get_meta_map()
        assert len(m2) == 2
        assert m2 == {
            '__initialized': m1['__initialized'], '__version': rstring('2')}

        hdf.add_meta_map({'__test': 1}, replace=True, init=True)
        m3 = hdf.get_meta_map()
        assert m3 == {'__test': rint(1)}

        hdf.cleanup()

    def testStringCol(self):
        # Tables size is in bytes, len("მიკროსკოპის პონი".encode()) == 46
        bytesize = 46
        hdf = HdfStorage(self.hdfpath(), self.lock)
        cols = [omero.columns.StringColumnI(
            "name", "description", bytesize, None)]
        hdf.initialize(cols)
        cols[0].settable(hdf._HdfStorage__mea)  # Needed for size
        cols[0].values = ["foo", "მიკროსკოპის პონი"]
        hdf.append(cols)
        rows = hdf.getWhereList(time.time(), '(name=="foo")', None, 'b', None,
                                None, None)
        assert rows == [0]
        assert bytesize == hdf.readCoordinates(
            time.time(), [0], self.current).columns[0].size
        # Unicode conditions don't work on Python 3
        # Fetching should still work though
        r1 = hdf.readCoordinates(time.time(), [1], self.current)
        assert len(r1.columns) == 1
        assert len(r1.columns[0].values) == 1
        assert r1.columns[0].size == bytesize
        assert r1.columns[0].values[0] == "მიკროსკოპის პონი"

        r2 = hdf.read(time.time(), [0], 0, 2, self.current)
        assert len(r2.columns) == 1
        assert len(r2.columns[0].values) == 2
        assert r2.columns[0].size == bytesize
        assert r2.columns[0].values[0] == "foo"
        assert r2.columns[0].values[1] == "მიკროსკოპის პონი"

        # Doesn't work yet.
        hdf.cleanup()

    def testStringColUnicodeSize(self):
        # len("მიკროსკოპის პონი") == 16
        # len("მიკროსკოპის პონი".encode()) == 46
        bytesize = 45
        hdf = HdfStorage(self.hdfpath(), self.lock)
        cols = [omero.columns.StringColumnI(
            "name", "description", bytesize, None)]
        hdf.initialize(cols)
        cols[0].settable(hdf._HdfStorage__mea)  # Needed for size
        cols[0].values = ["მიკროსკოპის პონი"]

        with pytest.raises(omero.ValidationException) as exc_info:
            hdf.append(cols)
        assert exc_info.value.message == (
            'Maximum string (byte) length in column name is 45')

        # Doesn't work yet.
        hdf.cleanup()

    @pytest.mark.xfail(reason=(
        "Unicode conditions broken on Python 3. "
        "See explanation in omero.columns.StringColumnI"))
    @pytest.mark.broken(reason="Unicode conditions broken on Python 3")
    def testStringColWhereUnicode(self):
        # Tables size is in bytes, len("მიკროსკოპის პონი".encode()) == 46
        bytesize = 46
        hdf = HdfStorage(self.hdfpath(), self.lock)
        cols = [omero.columns.StringColumnI(
            "name", "description", bytesize, None)]
        hdf.initialize(cols)
        cols[0].settable(hdf._HdfStorage__mea)  # Needed for size
        cols[0].values = ["foo", "მიკროსკოპის პონი"]
        hdf.append(cols)
        rows = hdf.getWhereList(time.time(), '(name=="მიკროსკოპის პონი")',
                                None, 'b', None, None, None)
        assert rows == [1]
        assert bytesize == hdf.readCoordinates(
            time.time(), [0], self.current).columns[0].size
        # Doesn't work yet.
        hdf.cleanup()

    def testRead(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        cols = [
            omero.columns.LongColumnI('a'),
            omero.columns.LongColumnI('b'),
            omero.columns.LongColumnI('c')]
        hdf.initialize(cols)
        cols[0].values = [1, 2, 3]
        cols[1].values = [4, 5, 6]
        cols[2].values = [7, 8, 9]
        hdf.append(cols)

        data = hdf.read(time.time(), [0, 1, 2], 0, 2, self.current)
        assert len(data.columns) == 3
        assert len(data.columns[0].values) == 2
        assert data.columns[0].name == 'a'
        assert data.columns[0].values[0] == 1
        assert data.columns[0].values[1] == 2
        assert data.columns[1].name == 'b'
        assert data.columns[1].values[0] == 4
        assert data.columns[1].values[1] == 5
        assert data.columns[2].name == 'c'
        assert data.columns[2].values[0] == 7
        assert data.columns[2].values[1] == 8
        assert data.rowNumbers == [0, 1]

        data = hdf.read(time.time(), [0, 2], 1, 3, self.current)
        assert len(data.columns) == 2
        assert len(data.columns[0].values) == 2
        assert data.columns[0].name == 'a'
        assert data.columns[0].values[0] == 2
        assert data.columns[0].values[1] == 3
        assert data.columns[1].name == 'c'
        assert data.columns[1].values[0] == 8
        assert data.columns[1].values[1] == 9
        assert data.rowNumbers == [1, 2]

        # Reads row 1
        data = hdf.read(time.time(), [1], 1, 2, self.current)
        assert len(data.columns) == 1
        assert len(data.columns[0].values) == 1
        assert data.columns[0].name == 'b'
        assert data.columns[0].values[0] == 5
        assert data.rowNumbers == [1]

       # Reads no row
        data = hdf.read(time.time(), [0, 1, 2], 1, 1, self.current)
        assert len(data.columns) == 3
        assert len(data.columns[0].values) == 0
        assert data.rowNumbers == []

        # Read all rows
        data = hdf.read(time.time(), [0, 1, 2], None, None, self.current)
        assert len(data.columns) == 3
        assert len(data.columns[0].values) == 3
        assert data.columns[0].name == 'a'
        assert data.columns[0].values[0] == 1
        assert data.columns[0].values[1] == 2
        assert data.columns[0].values[2] == 3
        assert data.columns[1].name == 'b'
        assert data.columns[1].values[0] == 4
        assert data.columns[1].values[1] == 5
        assert data.columns[1].values[2] == 6
        assert data.columns[2].name == 'c'
        assert data.columns[2].values[0] == 7
        assert data.columns[2].values[1] == 8
        assert data.columns[2].values[2] == 9
        assert data.rowNumbers == [0, 1, 2]

        # Read from row 1 until the end of the table
        data = hdf.read(time.time(), [0, 2], 1, None, self.current)
        assert len(data.columns) == 2
        assert len(data.columns[0].values) == 2
        assert data.columns[0].name == 'a'
        assert data.columns[0].values[0] == 2
        assert data.columns[0].values[1] == 3
        assert data.columns[1].name == 'c'
        assert data.columns[1].values[0] == 8
        assert data.columns[1].values[1] == 9
        assert data.rowNumbers == [1, 2]
        hdf.cleanup()

    #
    # ROIs
    #
    def testMaskColumn(self):
        hdf = HdfStorage(self.hdfpath(), self.lock)
        mask = omero.columns.MaskColumnI('mask', 'desc', None)
        hdf.initialize([mask], None)
        mask.imageId = [1, 2]
        mask.theZ = [2, 2]
        mask.theT = [3, 3]
        mask.x = [4, 4]
        mask.y = [5, 5]
        mask.w = [6, 6]
        mask.h = [7, 7]
        mask.bytes = [[0], [0, 1, 2, 3, 4]]
        hdf.append([mask])
        data = hdf.readCoordinates(hdf._stamp, [0, 1], self.current)
        assert len(data.columns) == 1
        assert len(data.columns[0].imageId) == 2
        assert 1 == data.columns[0].imageId[0]
        assert 2 == data.columns[0].theZ[0]
        assert 3 == data.columns[0].theT[0]
        assert 4 == data.columns[0].x[0]
        assert 5 == data.columns[0].y[0]
        assert 6 == data.columns[0].w[0]
        assert 7 == data.columns[0].h[0]
        assert [0] == data.columns[0].bytes[0]

        assert 2 == data.columns[0].imageId[1]
        assert 2 == data.columns[0].theZ[1]
        assert 3 == data.columns[0].theT[1]
        assert 4 == data.columns[0].x[1]
        assert 5 == data.columns[0].y[1]
        assert 6 == data.columns[0].w[1]
        assert 7 == data.columns[0].h[1]
        assert [0, 1, 2, 3, 4] == data.columns[0].bytes[1]

        data = hdf.read(hdf._stamp, [0], 0, 1, self.current)
        assert len(data.columns) == 1
        assert len(data.columns[0].imageId) == 1
        assert 1 == data.columns[0].imageId[0]
        assert 2 == data.columns[0].theZ[0]
        assert 3 == data.columns[0].theT[0]
        assert 4 == data.columns[0].x[0]
        assert 5 == data.columns[0].y[0]
        assert 6 == data.columns[0].w[0]
        assert 7 == data.columns[0].h[0]
        assert [0] == data.columns[0].bytes[0]
        hdf.cleanup()


class TestHdfList(TestCase):

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.mox = mox.Mox()

    def hdfpath(self):
        tmpdir = self.tmpdir()
        return old_div(path(tmpdir), "test.h5")

    @pytest.mark.xfail
    @pytest.mark.broken(reason = "TODO after python3 migration")
    def testLocking(self, monkeypatch):
        lock1 = threading.RLock()
        hdflist2 = HdfList()
        lock2 = threading.RLock()
        tmp = str(self.hdfpath())

        # Using HDFLIST
        hdf1 = HdfStorage(tmp, lock1)

        # There are multiple guards against opening the same HDF5 file

        # PyTables includes a check
        monkeypatch.setattr(storage_module, 'HDFLIST', hdflist2)
        with pytest.raises(ValueError) as exc_info:
            HdfStorage(tmp, lock2)

        assert exc_info.value.message.startswith(
            "The file '%s' is already opened. " % tmp)
        monkeypatch.undo()

        # HdfList uses portalocker, test by mocking tables.open_file
        if hasattr(tables, "open_file"):
            self.mox.StubOutWithMock(tables, 'open_file')
            tables.file._FILE_OPEN_POLICY = 'default'
            tables.open_file(tmp, mode='w',
                             title='OMERO HDF Measurement Storage',
                             rootUEP='/').AndReturn(open(tmp))

            self.mox.ReplayAll()
        else:
            self.mox.StubOutWithMock(tables, 'openFile')
            tables.openFile(tmp, mode='w',
                            title='OMERO HDF Measurement Storage',
                            rootUEP='/').AndReturn(open(tmp))

        monkeypatch.setattr(storage_module, 'HDFLIST', hdflist2)
        with pytest.raises(omero.LockTimeout) as exc_info:
            HdfStorage(tmp, lock2)
        print(exc_info.value)
        assert (exc_info.value.message ==
                'Cannot acquire exclusive lock on: %s' % tmp)

        monkeypatch.undo()

        hdf1.cleanup()

        self.mox.UnsetStubs()
        self.mox.VerifyAll()
