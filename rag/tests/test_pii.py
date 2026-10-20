import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from logging_store import mask_personal_data


class MaskPersonalDataTest(unittest.TestCase):
    def test_iban_is_masked(self):
        masked = mask_personal_data("Mi IBAN es ES91 2100 0418 4502 0005 1332")
        self.assertIn("[IBAN]", masked)
        self.assertNotIn("2100", masked)

    def test_dni_and_nie_are_masked(self):
        self.assertIn("[DNI]", mask_personal_data("Mi DNI es 12345678Z"))
        self.assertIn("[DNI]", mask_personal_data("Mi NIE es X1234567L"))

    def test_email_is_masked(self):
        masked = mask_personal_data("Escribidme a juan.perez@correo.com")
        self.assertIn("[EMAIL]", masked)
        self.assertNotIn("juan", masked)

    def test_card_number_is_masked(self):
        masked = mask_personal_data("Mi tarjeta 4111 1111 1111 1111 esta bloqueada")
        self.assertIn("[CARD]", masked)
        self.assertNotIn("4111", masked)

    def test_phone_is_masked(self):
        self.assertIn("[PHONE]", mask_personal_data("Llamame al 612 345 678"))
        self.assertIn("[PHONE]", mask_personal_data("Mi telefono es 612345678"))

    def test_amounts_and_years_are_kept(self):
        text = "Quiero una hipoteca de 200000 euros a 25 años al 3,5%"
        self.assertEqual(mask_personal_data(text), text)


if __name__ == "__main__":
    unittest.main()
