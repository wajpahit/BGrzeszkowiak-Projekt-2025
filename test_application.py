import unittest
from application import application
from unittest.mock import patch, MagicMock
import json

app=application
class FlaskAppTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        """Test czy strona główna zawiera oczekiwany tekst."""
        response = self.app.get('/')
        data = response.data.decode('utf-8')
        self.assertIn('Przelicznik walut z historią BLAD kursów', data)

    def test_page_loads(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_404_page(self):
        """Test czy aplikacja zwraca 404 dla nieistniejących stron"""
        response = self.app.get('/nieistniejaca_strona')
        self.assertEqual(response.status_code, 404)

    @patch('application.get_exchange_rate')
    @patch('application.get_exchange_rate_history')
    def test_calculate_endpoint(self, mock_history, mock_rate):
        """Test czy endpoint /calculate działa poprawnie"""
        mock_rate.return_value = 4.25
        mock_history.return_value = [
            {'relative_day': -1, 'date': '2025-05-18', 'day': 'Niedziela', 'rate': '4.2500',
             'calculated_value': '425.0000'},
            {'relative_day': -2, 'date': '2025-05-17', 'day': 'Sobota', 'rate': '4.2400',
             'calculated_value': '424.0000'}
        ]

        response = self.app.post('/calculate',
                                 json={'currency': 'eur', 'amount': '100'},
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['result'], '425.0000')
        self.assertIn('history_html', data)
        self.assertIn('Niedziela', data['history_html'])
        self.assertIn('425.0000', data['history_html'])
        self.assertIn('424.0000', data['history_html'])

    @patch('application.get_exchange_rate')
    @patch('application.get_exchange_rate_history')
    def test_calculated_value_in_history(self, mock_history, mock_rate):
        """Test czy pole calculated_value jest poprawnie obliczane i wyświetlane"""
        mock_rate.return_value = 3.85
        mock_history.return_value = [
            {'relative_day': 0, 'date': '2025-05-26', 'day': 'Poniedziałek', 'rate': '3.8500',
             'calculated_value': '192.5000'},
            {'relative_day': -1, 'date': '2025-05-25', 'day': 'Niedziela', 'rate': '3.8400',
             'calculated_value': '192.0000'},
            {'relative_day': -2, 'date': '2025-05-24', 'day': 'Sobota', 'rate': '3.8300',
             'calculated_value': '191.5000'}
        ]

        response = self.app.post('/calculate',
                                 json={'currency': 'usd', 'amount': '50'},
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        history_html = data['history_html']
        self.assertIn('192.5000', history_html)
        self.assertIn('192.0000', history_html)
        self.assertIn('191.5000', history_html)
        self.assertIn('<td>192.5000</td>', history_html)

if __name__ == '__main__':
    unittest.main()
