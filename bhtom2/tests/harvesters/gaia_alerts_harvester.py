import json
import os
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import patch

from django.test import TestCase

from django.conf import settings
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target

from bhtom2.harvesters.gaia_alerts_harvester import fetch_alerts_csv, search_term_in_gaia_data, get, \
    GaiaAlertsHarvester, update_gaia_lc

from pyfakefs.fake_filesystem_unittest import Patcher

from bhtom2.exceptions.external_service import NoResultException, InvalidExternalServiceResponseException

from pandas import DataFrame

from bhtom2.models.reduced_datum_extra import ReducedDatumExtraData

sample_file_two_lines = """
#Name, Date, RaDeg, DecDeg, AlertMag, HistoricMag, HistoricStdDev, Class, Published, Comment, TNSid
Gaia21eeo,2021-09-07 02:07:38,111.55315,-39.30836,18.70,20.22,0.64,"unknown",2021-09-09 08:19:08,"~2 mag brightening in a faint Gaia source",AT2021yjn
Gaia21een,2021-09-07 01:59:33,113.25287,-31.98319,17.82,20.04,0.72,"unknown",2021-09-09 08:19:02,"3 mag outburst in Gaia source, previous events seen, candidate CV",AT2021yjm
"""

sample_file_three_lines = """
#Name, Date, RaDeg, DecDeg, AlertMag, HistoricMag, HistoricStdDev, Class, Published, Comment, TNSid
Gaia21eeo,2021-09-07 02:07:38,111.55315,-39.30836,18.70,20.22,0.64,"unknown",2021-09-09 08:19:08,"~2 mag brightening in a faint Gaia source",AT2021yjn
Gaia21een,2021-09-07 01:59:33,113.25287,-31.98319,17.82,20.04,0.72,"unknown",2021-09-09 08:19:02,"3 mag outburst in Gaia source, previous events seen, candidate CV",AT2021yjm
Gaia21edy,2021-09-06 16:50:31,295.16969,14.58495,17.17,19.29,0.73,"unknown",2021-09-07 22:18:30,"outburst of candidate CV MGAB-V829",AT2021ygr
"""

sample_lightcurve_three_correct_lines = """
#Date JD(TCB) averagemag
2014-09-19 02:49:08,2456919.61745,untrusted
2014-09-20 02:49:08,2456920.61745,NaN
2014-10-31 1:40:22,2456961.56970,18.91
"""


class TestGaiaAlertsHarvester(TestCase):

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value="something")
    def test_create_csv_cache_file_if_not_present(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            fetch_alerts_csv()
            self.assertTrue(os.path.exists(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv')))

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value="something")
    def test_update_csv_cache_file_if_present(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            fetch_alerts_csv()
            self.assertEqual(open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'r').read(), "something")

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value=sample_file_three_lines)
    def test_raise_no_result_exception_if_csv_correct_and_doesnt_contain_term_and_alerts_dont_contain_term(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)
            self.assertRaises(NoResultException, search_term_in_gaia_data, "Something")

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value="invalid response")
    def test_raise_invalid_exception_if_csv_correct_and_doesnt_contain_term_and_alerts_incorrect(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)
            self.assertRaises(InvalidExternalServiceResponseException, search_term_in_gaia_data, "Something")

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value=sample_file_three_lines)
    def test_return_term_if_csv_correct_and_doesnt_contain_term_and_alerts_correct(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)
            term_data: DataFrame = search_term_in_gaia_data("Gaia21edy")
            self.assertEqual(term_data['#Name'], "Gaia21edy")
            self.assertEqual(term_data[' Date'], '2021-09-06 16:50:31')
            self.assertEqual(term_data[' RaDeg'], 295.16969)

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value=sample_file_three_lines)
    def test_return_term_if_csv_correct_and_contains_term(self, mocked_query):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)
            term_data: DataFrame = search_term_in_gaia_data("Gaia21eeo")
            self.assertEqual(term_data['#Name'], "Gaia21eeo")
            self.assertEqual(term_data[' Date'], '2021-09-07 02:07:38')
            self.assertEqual(term_data[' RaDeg'], 111.55315)
            self.assertFalse(mocked_query.called)

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value=sample_file_three_lines)
    def test_get_term_dict_if_csv_correct_and_doesnt_contain_term_and_alerts_correct(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)
            term_result: Dict[str, Any] = get("Gaia21edy")
            expected_result: Dict[str, Any] = {
                "gaia_name": "Gaia21edy",
                "ra": Decimal(295.16969),
                "dec": Decimal(14.58495),
                "disc": "2021-09-06 16:50:31",
                "classif": "unknown"
            }
            self.assertEqual(term_result, expected_result)

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value=sample_file_three_lines)
    def test_get_term_dict_if_csv_correct_and_contains_term(self, mocked_query):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)
            term_result: Dict[str, Any] = get("Gaia21eeo")
            expected_result: Dict[str, Any] = {
                "gaia_name": "Gaia21eeo",
                "ra": Decimal(111.55315),
                "dec": Decimal(-39.30836),
                "disc": "2021-09-07 02:07:38",
                "classif": "unknown"
            }
            self.assertEqual(term_result, expected_result)
            self.assertFalse(mocked_query.called)

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service', return_value=sample_file_three_lines)
    def test_get_target_if_csv_correct_and_doesnt_contain_term_and_alerts_correct(self, _):
        with Patcher() as patcher:
            patcher.fs.create_dir(os.path.join(settings.BASE_DIR, 'cache'))
            patcher.fs.create_file(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'))
            with open(os.path.join(settings.BASE_DIR, 'cache/gaia_alerts.csv'), 'w') as w:
                w.write(sample_file_two_lines)

            harvester = GaiaAlertsHarvester()
            harvester.query("Gaia21edy")
            target: Target = harvester.to_target()

            expected_target: Target = Target(name="Gaia21edy",
                                             ra=Decimal(295.16969),
                                             dec=Decimal(14.58495),
                                             type='SIDEREAL',
                                             epoch=2000, )

            self.assertEqual(target.name, "Gaia21edy")
            self.assertEqual(target.ra, Decimal(295.16969))
            self.assertEqual(target.dec, Decimal(14.58495))
            self.assertEqual(target.type, 'SIDEREAL')
            self.assertEqual(target.epoch, 2000)
            self.assertEqual(target.gaia_alert_name, "Gaia21edy")
            self.assertEqual(target.discovery_date, "2021-09-06 16:50:31")

    @patch('bhtom2.harvesters.gaia_alerts_harvester.query_external_service',
           return_value=sample_lightcurve_three_correct_lines)
    @patch('bhtom2.harvesters.gaia_alerts_harvester.refresh_reduced_data_view')
    def test_update_lightcurve(self, _, mocked_refresh):
        target: Target = Target(
            name="Gaia21edy",
            ra=Decimal(295.16969),
            dec=Decimal(14.58495),
            type='SIDEREAL',
            epoch=2000,
        )

        target.gaia_alert_name = "Gaia21edy"

        update_gaia_lc(target)

        rd: ReducedDatum = ReducedDatum.objects.all()[0]
        rded: ReducedDatumExtraData = ReducedDatumExtraData.objects.all()[0]

        self.assertEqual(rd.value, json.dumps({
            'magnitude': 18.91,
            'filter': 'G_Gaia',
            'error': 0,
            'jd': 2456961.56970
        }))
        self.assertEqual(rd.data_type, 'photometry')
        self.assertEqual(rd.target, target)

        self.assertEqual(rded.reduced_datum, rd)

        extra_data = json.loads(rded.extra_data)

        self.assertEqual(extra_data["facility"], "Gaia")
        self.assertEqual(extra_data["owner"], "Gaia")

        self.assertTrue(mocked_refresh.called)