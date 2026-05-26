"""
Tests for the payments SMS parser.
"""
from decimal import Decimal
from django.test import TestCase
from .sms_parser import parse_sms


class SmsParserStandardFormatTests(TestCase):
    """Tests for the standard SEND/TRANSFER command format."""

    def test_send_bank_to_momo(self):
        """SEND from BANK to MOMO with reference."""
        text = "SEND 200000 TZS FROM BANK 00922820111301 TO MOMO 0755123456 REF=Deposit_for_Kalton"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('200000'))
        self.assertEqual(result['currency'], 'TZS')
        self.assertEqual(result['from_account'], '00922820111301')
        self.assertEqual(result['from_account_type'], 'BANK')
        self.assertEqual(result['to_account'], '0755123456')
        self.assertEqual(result['to_account_type'], 'MOMO')
        self.assertEqual(result['reference'], 'Deposit_for_Kalton')
        self.assertEqual(result['parse_confidence'], 0.95)

    def test_send_momo_to_bank(self):
        """SEND from MOMO to BANK."""
        text = "SEND 50000 TZS FROM MOMO 0712345678 TO BANK 032175003282 REF=Ulete_na_kalton"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('50000'))
        self.assertEqual(result['from_account'], '0712345678')
        self.assertEqual(result['from_account_type'], 'MOMO')
        self.assertEqual(result['to_account'], '032175003282')
        self.assertEqual(result['to_account_type'], 'BANK')

    def test_send_intl_to_bank(self):
        """SEND in USD from INTL to BANK."""
        text = "SEND 100 USD FROM INTL GB12MIDL402234 TO BANK 01J7****200 REF=Western_Union_123"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('100'))
        self.assertEqual(result['currency'], 'USD')
        self.assertEqual(result['from_account'], 'GB12MIDL402234')
        self.assertEqual(result['from_account_type'], 'INTL')

    def test_send_momo_to_momo(self):
        """SEND from MOMO to MOMO."""
        text = "SEND 30000 TZS FROM MOMO 0688123456 TO MOMO 0788987654 REF=chakula"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('30000'))
        self.assertEqual(result['to_account'], '0788987654')

    def test_transfer_with_amount_equals(self):
        """TRANSFER format with AMOUNT= prefix."""
        text = "TRANSFER AMOUNT=4990000 TZS FROM BANK 52810027160 TO BANK 00922820111301"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('4990000'))
        self.assertEqual(result['currency'], 'TZS')
        self.assertEqual(result['from_account'], '52810027160')
        self.assertEqual(result['to_account'], '00922820111301')

    def test_send_without_reference(self):
        """SEND without REF= should work."""
        text = "SEND 50000 TZS FROM MOMO 0712345678 TO BANK 032175003282"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('50000'))
        self.assertIsNone(result.get('reference') or None)

    def test_send_with_comma_amount(self):
        """Amounts with commas should parse correctly."""
        text = "SEND 1,500,000 TZS FROM BANK 00922820111301 TO MOMO 0755123456 REF=Rent"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('1500000'))


class SmsParserBankNotificationTests(TestCase):
    """Tests for bank notification SMS formats."""

    def test_mkombozi_notification(self):
        """Mkombozi bank deposit notification."""
        text = "Hawa Mkombozi bank Ndugu Juma umefanikiwa kuweka TZS 500000 AC 00922820111301 Maelezo: Malipo ya bidhaa Tarehe 23 Apr 2026 REF. MK-2026-0042"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('500000'))
        self.assertEqual(result['currency'], 'TZS')
        self.assertEqual(result['from_bank'], 'Mkombozi')
        self.assertEqual(result['sender_name'], 'Juma')
        self.assertEqual(result['to_account'], '00922820111301')
        self.assertEqual(result['memo'], 'Malipo ya bidhaa')
        self.assertEqual(result['reference'], 'MK-2026-0042')
        self.assertEqual(result['parse_confidence'], 0.8)

    def test_nbc_notification(self):
        """NBC bank deposit notification."""
        text = """Hawa NBC Muamala umekamilika Jina la muwekaji: Hanna Mwale 
Namba ya akaunti: 032175003282 
Kiasi: TSh 750000 
Trh: 15 Mei 2026 
Kumb no: NBC-REF-8765"""
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('750000'))
        self.assertEqual(result['from_bank'], 'NBC')
        self.assertEqual(result['sender_name'], 'Hanna Mwale')
        self.assertEqual(result['reference'], 'NBC-REF-8765')

    def test_nmb_notification(self):
        """NMB bank deposit notification."""
        text = "Hawa NMB MWANGAZA confirmed you have successfully deposited TZS. 2000000 to account number 52810027160"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('2000000'))
        self.assertEqual(result['from_bank'], 'NMB')
        self.assertEqual(result['reference'], 'MWANGAZA')
        self.assertEqual(result['to_account'], '52810027160')

    def test_crdb_notification(self):
        """CRDB bank deposit notification."""
        text = "Hawa ni CRDB Dear Customer, you have received TZS 350000 in your account number: 1234567890 2026-04-23T14:30 REF: CRDB-REF-2026"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('350000'))
        self.assertEqual(result['currency'], 'TZS')
        self.assertEqual(result['from_bank'], 'CRDB')
        self.assertEqual(result['to_account'], '1234567890')
        self.assertEqual(result['reference'], 'CRDB-REF-2026')

    def test_mwanga_notification(self):
        """Mwanga Hakika bank deposit notification."""
        text = "Hawa ni Mwanga Hakika bank TZS 1000000 Imewekwa kwenye akaunti 00922820111301 Tarehe 10 Mei 2026 Piga 1234 5678 ikiwa huutambui"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('1000000'))
        self.assertEqual(result['from_bank'], 'Mwanga Hakika')
        self.assertEqual(result['to_account'], '00922820111301')

    def test_azania_notification(self):
        """Azania bank deposit notification."""
        text = "Hawa ni Azania bank Ndugu Juma Omar, Kiasi cha TZS 2500000 Kimewekwa kwenye Akaunti yako inayoishia 2011 kutoka kwa Salim Hassan Akaunti inayoishia 5432 kumb; AZN-REF-2026-789"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('2500000'))
        self.assertEqual(result['from_bank'], 'Azania')
        self.assertEqual(result['receiver_name'], 'Juma Omar')
        self.assertEqual(result['sender_name'], 'Salim Hassan')
        self.assertEqual(result['to_account'], '2011')
        self.assertEqual(result['from_account'], '5432')
        self.assertEqual(result['reference'], 'AZN-REF-2026-789')


class SmsParserFallbackTests(TestCase):
    """Tests for fallback parsing (unrecognized formats)."""

    def test_unrecognized_format(self):
        """Unrecognized SMS should fallback to minimal extraction."""
        text = "Some random message with TZS 12345 and REF=ABC123"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('12345'))
        self.assertEqual(result['currency'], 'TZS')
        self.assertEqual(result['reference'], 'ABC123')
        self.assertEqual(result['parse_confidence'], 0.1)
        self.assertIn('Could not match', result['parse_notes'])

    def test_empty_text(self):
        """Empty text should return low confidence result."""
        result = parse_sms("")
        self.assertEqual(result['parse_confidence'], 0.1)

    def test_only_numbers(self):
        """Text with only numbers should still extract amount."""
        result = parse_sms("500000")
        self.assertEqual(result['amount'], Decimal('500000'))


class SmsParserEdgeCaseTests(TestCase):
    """Tests for edge cases in the SMS parser."""

    def test_case_insensitivity(self):
        """Commands should be case insensitive."""
        result1 = parse_sms("send 100 tzs from bank 123 to momo 456 ref=test")
        result2 = parse_sms("SEND 100 TZS FROM BANK 123 TO MOMO 456 REF=test")
        self.assertEqual(result1['amount'], result2['amount'])

    def test_extra_whitespace(self):
        """Extra whitespace should be handled."""
        text = "  SEND   50000   TZS   FROM   BANK   123   TO   MOMO   456   REF=test  "
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('50000'))

    def test_reference_with_colon(self):
        """REF: syntax should work as well as REF=."""
        text = "SEND 100000 TZS FROM BANK 123 TO MOMO 456 REF: test_ref"
        result = parse_sms(text)
        self.assertEqual(result['reference'], 'test_ref')

    def test_amount_with_decimal(self):
        """Decimal amounts should parse correctly."""
        text = "SEND 1500.50 TZS FROM BANK 123 TO MOMO 456 REF=payment"
        result = parse_sms(text)
        self.assertEqual(result['amount'], Decimal('1500.50'))
