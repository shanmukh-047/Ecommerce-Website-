from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Address, IndianStates, User


class AddressAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="owner@malenadu.in", phone_number="9876511111", password="Password123!"
        )
        self.user2 = User.objects.create_user(
            email="attacker@malenadu.in", phone_number="9876522222", password="Password123!"
        )
        self.address_list_url = reverse("auth:address-list-create")

    def test_create_and_list_address(self):
        self.client.force_authenticate(user=self.user1)
        payload = {
            "recipient_name": "Sharada Hegde",
            "phone_number": "9876511111",
            "address_line_1": "Areca Plantation, Near Forest Gate",
            "city": "Sirsi",
            "state": IndianStates.KARNATAKA,
            "pincode": "581401",
            "is_default_shipping": True,
        }
        res = self.client.post(self.address_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        address_id = res.json()["data"]["id"]

        # List addresses
        list_res = self.client.get(self.address_list_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        results = list_res.json()["data"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], address_id)

    def test_cross_user_idor_protection(self):
        """User2 must not be able to view, edit, or delete User1's address."""
        # Create address for user1
        addr = Address.objects.create(
            user=self.user1,
            recipient_name="User 1 Recipient",
            phone_number="9876511111",
            address_line_1="Private Location",
            city="Sirsi",
            state=IndianStates.KARNATAKA,
            pincode="581401",
        )
        detail_url = reverse("auth:address-detail", kwargs={"pk": addr.pk})

        # User2 attempts to access User1's address
        self.client.force_authenticate(user=self.user2)

        # GET should return 404 Not Found (zero information leak)
        get_res = self.client.get(detail_url)
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH should return 404 Not Found
        patch_res = self.client.patch(detail_url, {"city": "HackedCity"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE should return 404 Not Found
        del_res = self.client.delete(detail_url)
        self.assertEqual(del_res.status_code, status.HTTP_404_NOT_FOUND)

        # Confirm address was not modified or deleted
        addr.refresh_from_db()
        self.assertEqual(addr.city, "Sirsi")

    def test_pincode_validation(self):
        self.client.force_authenticate(user=self.user1)
        payload = {
            "recipient_name": "Test",
            "phone_number": "9876511111",
            "address_line_1": "Road 1",
            "city": "Bengaluru",
            "state": IndianStates.KARNATAKA,
            "pincode": "058140",  # Invalid pincode starting with 0
        }
        res = self.client.post(self.address_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pincode", res.json()["error"]["details"])

    def test_set_default_endpoints(self):
        self.client.force_authenticate(user=self.user1)
        addr1 = Address.objects.create(
            user=self.user1,
            recipient_name="Addr 1",
            phone_number="9876511111",
            address_line_1="Lane 1",
            city="Sirsi",
            state=IndianStates.KARNATAKA,
            pincode="581401",
            is_default_shipping=True,
        )
        addr2 = Address.objects.create(
            user=self.user1,
            recipient_name="Addr 2",
            phone_number="9876511111",
            address_line_1="Lane 2",
            city="Sirsi",
            state=IndianStates.KARNATAKA,
            pincode="581401",
            is_default_shipping=False,
        )

        set_default_url = reverse("auth:address-set-default", kwargs={"pk": addr2.pk})
        res = self.client.post(set_default_url, {"type": "shipping"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default_shipping)
        self.assertTrue(addr2.is_default_shipping)
