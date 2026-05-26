"""
SMS Parser Engine

Parses both:
1. Bank deposit notification SMS (Mkombozi, NBC, NMB, CRDB, Mwanga, Azania, etc.)
2. Standard command-format SMS (SEND/TRANSFER instructions)

Extracts structured payment data from unstructured SMS text.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_sms(text: str) -> dict:
    """
    Main entry point. Parses SMS text and returns a dict with extracted fields
    plus a confidence score.
    """
    text = text.strip()

    # Try standard command format first (SEND / TRANSFER)
    result = parse_standard_format(text)
    if result:
        return result

    # Try bank notification format
    result = parse_bank_notification(text)
    if result:
        return result

    # Fallback: minimal extraction
    return {
        'raw_sms': text,
        'amount': _extract_amount(text),
        'currency': _extract_currency(text),
        'reference': _extract_reference(text),
        'parse_confidence': 0.1,
        'parse_notes': 'Could not match any known SMS format',
    }


# ──────────────────────────────────────────────
#  Standard command format
# ──────────────────────────────────────────────

def parse_standard_format(text: str) -> dict | None:
    """
    Handles:
      SEND 200000 TZS FROM BANK 00922820111301 TO MOMO 0755123456 REF=Deposit_for_Kalton
      SEND 50000 TZS FROM MOMO 0712345678 TO BANK 032175003282 REF=Ulete_na_kalton
      TRANSFER AMOUNT=4990000 TZS FROM BANK 52810027160 TO BANK 00922820111301
      SEND 100 USD FROM INTL GB12MIDL402234 TO BANK 01J7****200 REF=Western_Union_123
      SEND 30000 TZS FROM MOMO 0688123456 TO MOMO 0788987654 REF=chakula
    """
    text = text.strip()

    # Match SEND or TRANSFER
    command_match = re.match(
        r'^(SEND|TRANSFER)\s+'
        r'(?:AMOUNT=)?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s+'
        r'(TZS|USD|EUR|GBP|KES|UGX|RWF|BIF)?\s*'
        r'FROM\s+(BANK|MOMO|INTL)\s+(\S+)\s+'
        r'TO\s+(BANK|MOMO|INTL)\s+(\S+)'
        r'(?:\s+REF[=:]\s*(.*))?',
        text, re.IGNORECASE
    )
    if not command_match:
        return None

    cmd = command_match.group(1).upper()
    amount_str = command_match.group(2).replace(',', '')
    currency = (command_match.group(3) or 'TZS').upper()
    from_type = command_match.group(4).upper()
    from_acct = command_match.group(5)
    to_type = command_match.group(6).upper()
    to_acct = command_match.group(7)
    reference = (command_match.group(8) or '').strip()

    amount = _to_decimal(amount_str)
    memo = f"{cmd} request"
    if reference:
        memo = reference.replace('_', ' ')

    return {
        'raw_sms': text,
        'amount': amount,
        'currency': currency,
        'from_account': from_acct,
        'from_account_type': from_type,
        'to_account': to_acct,
        'to_account_type': to_type,
        'reference': reference,
        'memo': memo,
        'parse_confidence': 0.95,
        'parse_notes': 'Parsed as standard command format',
    }


# ──────────────────────────────────────────────
#  Bank notification format
# ──────────────────────────────────────────────

BANK_PATTERNS = [
    {
        'name': 'Mkombozi',
        'regex': re.compile(
            r'Hawa\s+Mkombozi\s+bank\s+Ndugu\s+(\S+)?\s*'
            r'umefanikiwa\s+kuweka\s+TZS\s+(\d{1,15}(?:[.,]\d{1,2})?)\s+'
            r'AC\s+(\S+)\s*'
            r'Maelezo:\s*(.*?)\s*'
            r'Tarehe\s+(\d{1,2}\s+\w+\s+\d{4})\s+'
            r'REF\.\s*(\S+)',
            re.IGNORECASE
        ),
        'currency': 'TZS',
    },
    {
        'name': 'NBC',
        'regex': re.compile(
            r'Hawa\s+NBC\s+Muamala\s+umekamilika\s+'
            r'Jina\s+la\s+muwekaji[:\-]\s*(\S+(?:\s+\S+)*?)?\s+'
            r'Namba\s+ya\s+akaunti[:\-]\s*(\S+)\s+'
            r'Kiasi[:\-]\s*TSh\s*(\d{1,15}(?:[.,]\d{1,2})?)\s+'
            r'Trh[:\-]\s*(\S+(?:\s+\S+)*?)?\s+'
            r'Kumb\s+no[:\-]\s*(\S+)',
            re.IGNORECASE
        ),
        'currency': 'TZS',
    },
    {
        'name': 'NMB',
        'regex': re.compile(
            r'Hawa\s+NMB\s+(\S+)\s+confirmed\s+you\s+have\s+successfully\s+deposited\s+'
            r'TZS\.?\s*(\d{1,15}(?:[.,]\d{1,2})?)\s+'
            r'to\s+account\s+number\s+(\S+)',
            re.IGNORECASE
        ),
        'currency': 'TZS',
    },
    {
        'name': 'CRDB',
        'regex': re.compile(
            r'Hawa\s+ni\s+CRDB\s+Dear\s+Customer,\s*'
            r'you\s+have\s+received\s+(TZS|USD|EUR)?\s*'
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s+'
            r'in\s+your\s+account\s+number[:\-]\s*(\S+)\s+'
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})\s+'
            r'REF[:\-]\s*(\S+)',
            re.IGNORECASE
        ),
        'currency': 'TZS',
    },
    {
        'name': 'Mwanga Hakika',
        'regex': re.compile(
            r'Hawa\s+ni\s+Mwanga\s+Hakika\s+bank\s+'
            r'TZS\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s+'
            r'Imewekwa\s+kwenye\s+akaunti\s+(\S+)\s*'
            r'Tarehe\s+(\S+(?:\s+\S+)*?)?\s*'
            r'Piga\s+\S+(?:\s+\S+)*?\s+ikiwa\s+huutambui',
            re.IGNORECASE
        ),
        'currency': 'TZS',
    },
    {
        'name': 'Azania',
        'regex': re.compile(
            r'Hawa\s+ni\s+Azania\s+bank\s+'
            r'Ndugu\s+(\S+(?:\s+\S+)*?)?,\s*'
            r'Kiasi\s+cha\s+TZS\s*'
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s+'
            r'Kimewekwa\s+kwenye\s+Akaunti\s+yako\s+inayoishia\s+(\S+)\s+'
            r'kutoka\s+kwa\s+(\S+(?:\s+\S+)*?)?\s+'
            r'Akaunti\s+inayoishia\s+(\S+)\s+'
            r'kumb[;:]\s*(\S+)',
            re.IGNORECASE
        ),
        'currency': 'TZS',
    },
]


def parse_bank_notification(text: str) -> dict | None:
    """Try to parse text as a bank deposit notification SMS."""
    for bank in BANK_PATTERNS:
        m = bank['regex'].search(text)
        if not m:
            continue

        name = bank['name']
        currency = bank['currency']
        groups = m.groups()

        result = {
            'raw_sms': text,
            'currency': currency,
            'from_bank': name,
            'parse_confidence': 0.8,
            'parse_notes': f'Parsed as {name} bank notification',
        }

        if name == 'Mkombozi':
            result['sender_name'] = _clean(groups[0])
            result['amount'] = _to_decimal(groups[1])
            result['to_account'] = _clean(groups[2])
            result['memo'] = _clean(groups[3])
            result['reference'] = _clean(groups[5])
            # Try to parse date
            date_str = _clean(groups[4])
            result['transaction_date'] = _parse_swahili_date(date_str)

        elif name == 'NBC':
            result['sender_name'] = _clean(groups[0])
            result['to_account'] = _clean(groups[1])
            result['amount'] = _to_decimal(groups[2])
            date_str = _clean(groups[3])
            result['transaction_date'] = _parse_swahili_date(date_str)
            result['reference'] = _clean(groups[4])

        elif name == 'NMB':
            result['reference'] = _clean(groups[0])
            result['amount'] = _to_decimal(groups[1])
            result['to_account'] = _clean(groups[2])

        elif name == 'CRDB':
            ccy = _clean(groups[0]) or 'TZS'
            result['currency'] = ccy
            result['amount'] = _to_decimal(groups[1])
            result['to_account'] = _clean(groups[2])
            try:
                result['transaction_date'] = datetime.strptime(
                    _clean(groups[3]), '%Y-%m-%dT%H:%M'
                )
            except (ValueError, IndexError):
                pass
            result['reference'] = _clean(groups[4])

        elif name == 'Mwanga Hakika':
            result['amount'] = _to_decimal(groups[0])
            result['to_account'] = _clean(groups[1])
            date_str = _clean(groups[2])
            result['transaction_date'] = _parse_swahili_date(date_str)

        elif name == 'Azania':
            result['receiver_name'] = _clean(groups[0])
            result['amount'] = _to_decimal(groups[1])
            result['to_account'] = _clean(groups[2])
            result['sender_name'] = _clean(groups[3])
            result['from_account'] = _clean(groups[4])
            result['reference'] = _clean(groups[5])

        return result

    return None


# ──────────────────────────────────────────────
#  Helper utilities
# ──────────────────────────────────────────────

MONTH_MAP_SWA = {
    'jan': 1, 'januari': 1,
    'feb': 2, 'februari': 2,
    'mar': 3, 'machi': 3,
    'apr': 4, 'april': 4,
    'mei': 5, 'may': 5,
    'jun': 6, 'juni': 6,
    'jul': 7, 'julai': 7,
    'aug': 8, 'agosti': 8,
    'sep': 9, 'septemba': 9,
    'oct': 10, 'oktoba': 10,
    'nov': 11, 'novemba': 11,
    'dec': 12, 'desemba': 12,
}


def _parse_swahili_date(date_str: str) -> datetime | None:
    """Parse dates like '23 Apr 2026', '02/05/2026', '01-May-2026', '5/2/2026'"""
    if not date_str:
        return None
    date_str = date_str.strip()

    # Try ISO format
    for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass

    # Try DD/MM/YYYY or MM/DD/YYYY
    m = re.match(r'(\d{1,2})[./](\d{1,2})[./](\d{4})', date_str)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d)
        except ValueError:
            try:
                return datetime(y, d, mo)
            except ValueError:
                pass

    # Try '23 Apr 2026' (Swahili/English month names)
    m = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
    if m:
        day = int(m.group(1))
        month_str = m.group(2).lower()[:3]
        year = int(m.group(3))
        month = MONTH_MAP_SWA.get(month_str)
        if month:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

    # Try '01-May-2026'
    m = re.match(r'(\d{1,2})-(\w+)-(\d{4})', date_str)
    if m:
        day = int(m.group(1))
        month_str = m.group(2).lower()[:3]
        year = int(m.group(3))
        month = MONTH_MAP_SWA.get(month_str)
        if month:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

    return None


def _extract_amount(text: str) -> Decimal | None:
    """Fallback: find any number in the text."""
    m = re.search(r'(\d{1,15}(?:[.,]\d{1,2})?)', text.replace(',', ''))
    if m:
        return _to_decimal(m.group(1))
    return None


def _extract_currency(text: str) -> str | None:
    """Fallback: find currency code."""
    m = re.search(r'\b(TZS|USD|EUR|GBP|KES|UGX|RWF|BIF|TSh)\b', text)
    if m:
        return m.group(1).upper()
    return None


def _extract_reference(text: str) -> str | None:
    """Fallback: find reference string."""
    m = re.search(r'REF[.:=\s]*(\S+)', text)
    if m:
        return m.group(1)
    m = re.search(r'Kumb\s+no[:\-]\s*(\S+)', text)
    if m:
        return m.group(1)
    return None


def _to_decimal(s: str | None) -> Decimal | None:
    if s is None:
        return None
    try:
        return Decimal(str(s).replace(',', '').strip())
    except (InvalidOperation, ValueError):
        return None


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip().strip('.,;:')
    return s if s else None
