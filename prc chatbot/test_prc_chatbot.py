import unittest
import json
import os
import sys

# Ensure prc_chatbot can be imported
sys.path.insert(0, os.path.dirname(__file__))
from prc_chatbot import app, find_faq_reply, FAQS


class PRCChatbotTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'College Enquiry Chatbot', response.data)

    def test_faqs_endpoint(self):
        response = self.client.get('/faqs')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 8)

    def test_message_matching(self):
        # Exact keyword match with word boundaries
        reply_ba = find_faq_reply("Do you offer a BA course?")
        self.assertIsNotNone(reply_ba)
        self.assertIn("undergraduate programmes", reply_ba)

        # Word boundary check - "basketball" should NOT match keyword "ba"
        reply_basketball = find_faq_reply("Do you have a basketball court?")
        self.assertNotEqual(reply_basketball, reply_ba)

    def test_conversational_intents(self):
        # Greetings
        reply_hi = find_faq_reply("hello there")
        self.assertIsNotNone(reply_hi)
        self.assertIn("Welcome to our College Enquiry Helpdesk", reply_hi)

        # Thanks
        reply_thanks = find_faq_reply("thank you so much")
        self.assertIsNotNone(reply_thanks)
        self.assertIn("You're very welcome", reply_thanks)

        # Bye
        reply_bye = find_faq_reply("goodbye")
        self.assertIsNotNone(reply_bye)
        self.assertIn("Goodbye!", reply_bye)

        # Bot help
        reply_help = find_faq_reply("who are you")
        self.assertIsNotNone(reply_help)
        self.assertIn("College Enquiry Virtual Assistant", reply_help)

    def test_admin_flow(self):
        # GET /admin without login redirects to /login
        res_unauth = self.client.get('/admin')
        self.assertEqual(res_unauth.status_code, 302)

        # Login with default credentials
        res_login = self.client.post('/login', data={'username': 'admin', 'password': 'password'}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'FAQ Admin', res_login.data)

        # Add a new FAQ
        res_add = self.client.post('/admin', data={
            'question': 'What are library hours?',
            'answer': 'The library is open 24/7 during semester.',
            'keywords': 'library, hours'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b'What are library hours?', res_add.data)

    def test_logout(self):
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    unittest.main()
