import requests
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import logging

application = Flask(__name__)

# Konfiguracja logowania
'''logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
application.logger.setLevel(logging.DEBUG)
'''
application.logger.setLevel(logging.CRITICAL)

CURRENCIES = {
    'usd': 'USD',
    'eur': 'EUR',
    'chf': 'CHF',
    'gbp': 'GBP'
}

DAY_TRANSLATIONS = {
    'Monday': 'Poniedziałek',
    'Tuesday': 'Wtorek',
    'Wednesday': 'Środa',
    'Thursday': 'Czwartek',
    'Friday': 'Piątek',
    'Saturday': 'Sobota',
    'Sunday': 'Niedziela'
}


def get_exchange_rate(currency_code):
    application.logger.debug("Pobieranie aktualnych kursów walut")
    url = f'https://api.nbp.pl/api/exchangerates/rates/A/{currency_code}/?format=json'
    response = requests.get(url)
    data = response.json()
    exchange = data['rates'][0]['mid']
    application.logger.debug(f"Pobrano kurs: {exchange}")
    return exchange

'''
more general version of get_exchange_rate to get all rates related to CURRENCIES.values()
def get_exchange_rates():
    application.logger.debug("Pobieranie aktualnych kursów walut")
    url = 'https://api.nbp.pl/api/exchangerates/tables/A?format=json'
    response = requests.get(url)
    data = response.json()
    rates = data[0]['rates']

    exchange = {}
    for code in CURRENCIES.values():
        entry = next((item for item in rates if item['code'] == code), None)
        if entry:
            exchange[code.lower()] = entry['mid']

    application.logger.debug(f"Pobrano kursy: {exchange}")
    return exchange
'''


def get_exchange_rate_history(currency_code, amount=1.0):
    application.logger.debug(f"Rozpoczęcie generowania historii dla {currency_code}")
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    try:
        url = f'https://api.nbp.pl/api/exchangerates/rates/A/{currency_code}/{start_date}/{end_date}/?format=json'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rates = data.get('rates', [])

        history = []
        today = datetime.now().date()

        for rate in rates:
            date_obj = datetime.strptime(rate['effectiveDate'], '%Y-%m-%d').date()
            delta_days = (today - date_obj).days
            #Pomin dzisiejszy dzień o ile pojawi się w historii
            if delta_days == 0:
                continue
            rate_value = rate['mid']
            calculated_value = amount * rate_value
            history.append({
                'relative_day': -delta_days,
                'date': rate['effectiveDate'],
                'day': DAY_TRANSLATIONS.get(date_obj.strftime('%A'), date_obj.strftime('%A')),
                'rate': f"{rate_value:.4f}",
                'calculated_value': f"{calculated_value:.4f}"
            })

        application.logger.debug(f"Wygenerowano historię {len(history)} rekordów")
        return sorted(history, key=lambda x: x['relative_day'],reverse=True)

    except requests.exceptions.RequestException as e:
        application.logger.error(f"Błąd podczas pobierania historii: {str(e)}")
        return []

@application.route('/')
def index():
    application.logger.debug("Ładowanie strony głównej")
    return render_template('index.html', currencies=CURRENCIES)


@application.route('/calculate', methods=['POST'])
def calculate():
    application.logger.debug("Otrzymano żądanie obliczeniowe")
    data = request.get_json()
    currency = data.get('currency')
    amount = data.get('amount')

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        application.logger.warning("Nieprawidłowa wartość kwoty")
        return jsonify({'error': 'Nieprawidłowa wartość'}), 400

    rate = get_exchange_rate(currency)

    if not rate:
        application.logger.error(f"Brak kursu dla waluty {currency}")
        return jsonify({'error': 'Brak kursu dla wybranej waluty'}), 400

    result = f"{amount * rate:.4f}"
    # Przekaż kwotę do funkcji historii
    history = get_exchange_rate_history(CURRENCIES[currency].upper(), amount)

    application.logger.debug("Generowanie szablonu historii")
    history_html = render_template('history_table.html', history=history)
    application.logger.debug("Pomyślnie wygenerowano szablon historii")

    return jsonify({
        'result': result,
        'history_html': history_html
    })

if __name__ == '__main__':
    application.run(debug=True)
