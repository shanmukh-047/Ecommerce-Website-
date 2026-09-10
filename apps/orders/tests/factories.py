from apps.accounts.models import (
    Address,
    IndianStates,
    Role,
    User,
    VerificationStatus,
    WholesaleProfile,
)
from apps.cart.services import CartService


def create_order_user(email="order_user@example.com", phone="9876543201", role=Role.CUSTOMER):
    user = User.objects.create_user(email, phone, "StrongPassword123!")
    if role != Role.CUSTOMER:
        user.role = role
        user.save()
    return user


def create_wholesale_user(email="wholesale_order@example.com", phone="9876543202"):
    user = create_order_user(email, phone, role=Role.WHOLESALE_APPROVED)
    WholesaleProfile.objects.create(
        user=user,
        company_name="Malenadu Agro Spices",
        gstin="29ABCDE1234F1Z5",
        pan_number="ABCDE1234F",
        verification_status=VerificationStatus.APPROVED,
    )
    return user


def create_order_address(user, recipient_name="Ramesh Hegde"):
    return Address.objects.create(
        user=user,
        recipient_name=recipient_name,
        phone_number="9876543201",
        address_line_1="Devimane Ghat Road, Sirsi",
        address_line_2="Near Marikamba Temple",
        landmark="Spice Valley Estate",
        city="Sirsi",
        state=IndianStates.KARNATAKA,
        pincode="581401",
        is_default_shipping=True,
    )


def create_staff_user(email="staff_order@example.com", phone="9876543203"):
    return create_order_user(email, phone, role=Role.STAFF)


def add_to_cart(user, variant, quantity):
    cart = CartService.get_or_create_user_cart(user)
    return CartService.add_item(cart, variant, quantity)
