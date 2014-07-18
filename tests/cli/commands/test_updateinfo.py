# Copyright (C) 2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import dnf.pycomp
import dnf.cli.commands.updateinfo
import hawkey
import itertools
import shutil
import tempfile
import tests.mock
import tests.support


class UpdateInfoCommandTest(tests.support.TestCase):

    """Test case validating updateinfo commands."""

    def setUp(self):
        """Prepare the test fixture."""
        super(UpdateInfoCommandTest, self).setUp()
        cachedir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cachedir)
        self.cli = tests.support.MockBase().mock_cli()
        self.cli.base.add_test_dir_repo('rpm', cachedir)
        self._stdout = dnf.pycomp.StringIO()
        self.addCleanup(tests.mock.patch.stopall)
        tests.support.mock.patch(
            'dnf.cli.commands.updateinfo._',
            dnf.pycomp.NullTranslations().ugettext).start()
        tests.support.mock.patch(
            'dnf.cli.commands.updateinfo.print',
            self._stub_print, create=True).start()

    def _stub_print(self, *objects):
        """Pretend to print to standard output."""
        print(*objects, file=self._stdout)

    def test_installed_apkg_adv_insts(self):
        """Test installed triplets querying."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.refresh_installed_cache()
        mixed, apkg_adv_insts = cmd.installed_apkg_adv_insts()
        self.assertFalse(mixed, 'incorrect flag')
        self.assertCountEqual(
            ((apk.filename, adv.id, ins) for apk, adv, ins in apkg_adv_insts),
            [('tour-4-4.noarch.rpm', 'DNF-2014-1', True),
             ('tour-5-0.noarch.rpm', 'DNF-2014-2', True)],
            'incorrect pairs')
        cmd.clear_installed_cache()

    def test_updating_apkg_adv_insts(self):
        """Test updating triplets querying."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.refresh_installed_cache()
        mixed, apkg_adv_insts = cmd.updating_apkg_adv_insts()
        self.assertFalse(mixed, 'incorrect flag')
        self.assertCountEqual(
            ((apk.filename, adv.id, ins) for apk, adv, ins in apkg_adv_insts),
            [('tour-5-1.noarch.rpm', 'DNF-2014-3', False)],
            'incorrect pairs')
        cmd.clear_installed_cache()

    def test_all_apkg_adv_insts(self):
        """Test all triplets querying."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.refresh_installed_cache()
        mixed, apkg_adv_insts = cmd.all_apkg_adv_insts()
        self.assertTrue(mixed, 'incorrect flag')
        self.assertCountEqual(
            ((apk.filename, adv.id, ins) for apk, adv, ins in apkg_adv_insts),
            [('tour-4-4.noarch.rpm', 'DNF-2014-1', True),
             ('tour-5-0.noarch.rpm', 'DNF-2014-2', True),
             ('tour-5-1.noarch.rpm', 'DNF-2014-3', False)])
        cmd.clear_installed_cache()

    def test_all_apkg_adv_insts_filter_advisories(self):
        """Test querying with an advisories filter."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.refresh_installed_cache()
        mixed, apkg_adv_insts = cmd.all_apkg_adv_insts(
            ['DNF-201*-[13]', 'NO-0000-0'])
        self.assertTrue(mixed, 'incorrect flag')
        self.assertCountEqual(
            ((apk.filename, adv.id, ins) for apk, adv, ins in apkg_adv_insts),
            [('tour-4-4.noarch.rpm', 'DNF-2014-1', True),
             ('tour-5-1.noarch.rpm', 'DNF-2014-3', False)],
            'incorrect pairs')
        cmd.clear_installed_cache()

    def test_display_list_mixed(self):
        """Test list displaying with mixed installs."""
        apkg_adv_insts = itertools.chain(
            ((apkg, adv, False)
             for pkg in self.cli.base.sack.query().installed()
             for adv in pkg.get_advisories(hawkey.GT)
             for apkg in adv.packages),
            ((apkg, adv, True)
             for pkg in self.cli.base.sack.query().installed()
             for adv in pkg.get_advisories(hawkey.LT | hawkey.EQ)
             for apkg in adv.packages))
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.display_list(apkg_adv_insts, True, '')
        self.assertEqual(self._stdout.getvalue(),
                         'i DNF-2014-1 bugfix      tour-4-4.noarch\n'
                         'i DNF-2014-2 enhancement tour-5-0.noarch\n'
                         '  DNF-2014-3 security    tour-5-1.noarch\n',
                         'incorrect output')

    def test_display_info_verbose(self):
        """Test verbose displaying."""
        apkg_adv_insts = ((apkg, adv, False)
                     for pkg in self.cli.base.sack.query().installed()
                     for adv in pkg.get_advisories(hawkey.GT)
                     for apkg in adv.packages)
        self.cli.base.conf.verbose = True
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.display_info(apkg_adv_insts, False, '')
        updated = datetime.datetime.fromtimestamp(1404841143)
        self.assertEqual(self._stdout.getvalue(),
                         '========================================'
                         '=======================================\n'
                         '  tour-5-1\n'
                         '========================================'
                         '=======================================\n'
                         '  Update ID : DNF-2014-3\n'
                         '       Type : security\n'
                         '    Updated : ' + str(updated) + '\n'
                         'Description : testing advisory\n'
                         '      Files : tour-5-1.noarch.rpm\n'
                         '\n',
                         'incorrect output')

    def test_display_info_verbose_mixed(self):
        """Test verbose displaying with mixed installs."""
        apkg_adv_insts = itertools.chain(
            ((apkg, adv, False)
             for pkg in self.cli.base.sack.query().installed()
             for adv in pkg.get_advisories(hawkey.GT)
             for apkg in adv.packages),
            ((apkg, adv, True)
             for pkg in self.cli.base.sack.query().installed()
             for adv in pkg.get_advisories(hawkey.LT | hawkey.EQ)
             for apkg in adv.packages))
        self.cli.base.conf.verbose = True
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.display_info(apkg_adv_insts, True, '')
        updated1 = datetime.datetime.fromtimestamp(1404840841)
        updated2 = datetime.datetime.fromtimestamp(1404841082)
        updated3 = datetime.datetime.fromtimestamp(1404841143)
        self.assertEqual(self._stdout.getvalue(),
                         '========================================'
                         '=======================================\n'
                         '  tour-5-1\n'
                         '========================================'
                         '=======================================\n'
                         '  Update ID : DNF-2014-3\n'
                         '       Type : security\n'
                         '    Updated : ' + str(updated3) + '\n'
                         'Description : testing advisory\n'
                         '      Files : tour-5-1.noarch.rpm\n'
                         '  Installed : false\n'
                         '\n'
                         '========================================'
                         '=======================================\n'
                         '  tour-4-4\n'
                         '========================================'
                         '=======================================\n'
                         '  Update ID : DNF-2014-1\n'
                         '       Type : bugfix\n'
                         '    Updated : ' + str(updated1) + '\n'
                         'Description : testing advisory\n'
                         '      Files : tour-4-4.noarch.rpm\n'
                         '  Installed : true\n'
                         '\n'
                         '========================================'
                         '=======================================\n'
                         '  tour-5-0\n'
                         '========================================'
                         '=======================================\n'
                         '  Update ID : DNF-2014-2\n'
                         '       Type : enhancement\n'
                         '    Updated : ' + str(updated2) + '\n'
                         'Description : testing advisory\n'
                         '      Files : tour-5-0.noarch.rpm\n'
                         '  Installed : true\n'
                         '\n',
                         'incorrect output')

    # This test also tests the display_summary and available_apkg_adv_insts
    # methods.
    def test_run_available(self):
        """Test running with available advisories."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.run([])
        self.assertEqual(self._stdout.getvalue(),
                         'Updates Information Summary: available\n'
                         '    1 Security notice(s)\n',
                         'incorrect output')

    # This test also tests the display_list and available_apkg_adv_insts
    # methods.
    def test_run_list(self):
        """Test running the list sub-command."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.run(['list'])
        self.assertEqual(self._stdout.getvalue(),
                         'DNF-2014-3 security tour-5-1.noarch\n',
                         'incorrect output')

    # This test also tests the display_info and available_apkg_adv_insts
    # methods.
    def test_run_info(self):
        """Test running the info sub-command."""
        cmd = dnf.cli.commands.updateinfo.UpdateInfoCommand(self.cli)
        cmd.run(['info'])
        updated = datetime.datetime.fromtimestamp(1404841143)
        self.assertEqual(self._stdout.getvalue(),
                         '========================================'
                         '=======================================\n'
                         '  tour-5-1\n'
                         '========================================'
                         '=======================================\n'
                         '  Update ID : DNF-2014-3\n'
                         '       Type : security\n'
                         '    Updated : ' + str(updated) + '\n'
                         'Description : testing advisory\n'
                         '\n',
                         'incorrect output')
