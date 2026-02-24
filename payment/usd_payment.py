import requests
import logging
import config

class CryptoPayment:
    def __init__(self, crypto_token):
        self.token = crypto_token
        self.base_url = "https://pay.crypt.bot/api/"
    
    def create_invoice(self, amount, asset='USDT', currency='USD', description="Оплата подписки", paid_btn_name=None, paid_btn_url=None):
        try:
            headers = {
                'Crypto-Pay-API-Token': self.token,
                'Content-Type': 'application/json'
            }
            
            data = {
                'asset': asset,
                'amount': str(amount),
                'description': description,
                'hidden_message': 'Спасибо за оплату! Ваш доступ активирован.', 
                'paid_btn_name': 'viewItem' if paid_btn_name is None else paid_btn_name,  
                'paid_btn_url': 'https://t.me/your_channel' if paid_btn_url is None else paid_btn_url  
            }
            
            response = requests.post(
                f"{self.base_url}createInvoice",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    invoice = result['result']
                    return {
                        'success': True,
                        'invoice_id': invoice['invoice_id'],
                        'pay_url': invoice['pay_url'],
                        'amount': amount,
                        'asset': asset,
                        'description': description
                    }
                else:
                    error_msg = result.get('error', {}).get('name', 'Unknown error')
                    return {
                        'success': False,
                        'error': error_msg
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
            
        except Exception as e:
            logging.error(f"Crypto payment error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_payment(self, invoice_id):
        try:
            headers = {
                'Crypto-Pay-API-Token': self.token
            }
            
            response = requests.get(
                f"{self.base_url}getInvoices?invoice_ids={invoice_id}",
                headers=headers,
                timeout=10
            )
            
            logging.info(f"CryptoBot API response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logging.info(f"CryptoBot API result: {result}")
                
                if result.get('ok') and result['result'].get('items'):
                    invoice = result['result']['items'][0]
                    status = invoice.get('status')
                    
                  
                    logging.info(f"Invoice {invoice_id} status: {status}")
                    
                   
                    if status == 'paid':
                        return True
                    elif status == 'active':
                        # Счет создан, но не оплачен
                        return False
                    elif status in ['expired', 'cancelled']:
                        # Счет просрочен или отменен
                        return False
                    else:
                        logging.warning(f"Unknown invoice status: {status}")
                        return False
            
            logging.error(f"CryptoBot API error: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            logging.error(f"Crypto check error: {str(e)}")
            return False

class UsdPayment:
    def __init__(self):
        self.crypto_payment = CryptoPayment(config.crypto)
        self.logger = logging.getLogger('Payments')
    
    def create_invoice(self, amount, currency='USD', description="Оплата подписки"):
        try:
            invoice = self.crypto_payment.create_invoice(
                amount=amount,
                description=description,
                paid_btn_name='viewItem',
                paid_btn_url='https://t.me/your_channel' 
            )
            
            return invoice
            
        except Exception as e:
            self.logger.error(f"Payment creation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def check_payment(self, invoice_id):
        try:
            return self.crypto_payment.check_payment(invoice_id)
                
        except Exception as e:
            self.logger.error(f"Payment check error: {str(e)}")
            return False