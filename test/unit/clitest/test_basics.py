#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2015 University of Dundee & Open Microscopy Environment.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


from __future__ import unicode_literals
from builtins import object
import pytest
from omero.cli import CLI
import omero.util

cli = CLI()
cli.loadplugins()
commands = list(cli.controls.keys())
topics = list(cli.topics.keys())


class TestBasics(object):

    def testHelp(self):
        self.args = ["help", "-h"]
        cli.invoke(self.args, strict=True)

    @pytest.mark.parametrize('recursive', [None, "--recursive"])
    def testHelpAll(self, recursive):
        self.args = ["help", "--all"]
        if recursive:
            self.args.append(recursive)
        cli.invoke(self.args, strict=True)

    @pytest.mark.parametrize('recursive', [None, "--recursive"])
    @pytest.mark.parametrize('command', commands)
    def testHelpCommand(self, command, recursive):
        self.args = ["help", command]
        if recursive:
            self.args.append(recursive)
        cli.invoke(self.args, strict=True)

    @pytest.mark.parametrize('topic', topics)
    def testHelpTopic(self, topic):
        self.args = ["help", topic, "-h"]
        cli.invoke(self.args, strict=True)

    def testHelpList(self):
        self.args = ["help", "list"]
        cli.invoke(self.args, strict=True)

    def testQuit(object):
        cli.invoke(["quit"], strict=True)

    def testVersion(object):
        cli.invoke(["version"], strict=True)

    def testLoadGlob(object, monkeypatch, tmp_path, capsys):
        (tmp_path / 'etc').mkdir()
        (tmp_path / 'etc' / 'grid').mkdir()
        monkeypatch.setattr(
            "omero.util.get_omerodir", lambda throw: str(tmp_path))
        cli2 = CLI()
        cli2.dir = str(tmp_path)
        cli2.loadplugins()
        for i in 'abc':
            (tmp_path / (i + 'a.omero')).write_text(
                'config set {i} {i}'.format(i=i))
        cli2.invoke(["load", "--glob", str(tmp_path / '*.omero')], strict=True)
        cli2.invoke(["config", "get"], strict=True)
        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        assert lines == ['a=a', 'b=b', 'c=c']

    def testErrors(object, monkeypatch, tmp_path, capsys):
        cli.invoke(["errors"], strict=True)
        captured = capsys.readouterr()
        assert "52	       hql	 BAD_QUERY" in captured.out
