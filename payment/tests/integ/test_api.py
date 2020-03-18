import uuid
import pytest
import requests
from fixtures import iam_auth # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def payment_3p_api_url():
    return get_parameter("/ecommerce/{Environment}/payment-3p/api/url")


@pytest.fixture(scope="module")
def payment_api_url():
    return get_parameter("/ecommerce/{Environment}/payment/api/url")


def test_backend_validate(payment_3p_api_url, payment_api_url, iam_auth):
    """
    Test /backend/validate
    """

    card_number = "1234567890123456"
    total = 3000

    # Create a payment token
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": card_number,
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        auth=iam_auth(payment_api_url),
        json={
            "paymentToken": payment_token,
            "total": total
        }
    )

    assert res.status_code == 200
    body = res.json()
    assert "ok" in body
    assert "message" not in body
    assert body["ok"] == True

    # Cleanup
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })


def test_backend_validate_non_existent(payment_3p_api_url, payment_api_url, iam_auth):
    """
    Test /backend/validate with a non-existent token
    """

    payment_token = str(uuid.uuid4())
    total = 3000

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        auth=iam_auth(payment_api_url),
        json={
            "paymentToken": payment_token,
            "total": total
        }
    )

    assert res.status_code == 200
    body = res.json()
    assert "ok" in body
    assert "message" not in body
    assert body["ok"] == False


def test_backend_validate_smaller_total(payment_3p_api_url, payment_api_url, iam_auth):
    """
    Test /backend/validate with a smaller total
    """

    card_number = "1234567890123456"
    total = 3000

    # Create a payment token
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": card_number,
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        auth=iam_auth(payment_api_url),
        json={
            "paymentToken": payment_token,
            "total": total-1000
        }
    )

    assert res.status_code == 200
    body = res.json()
    assert "ok" in body
    assert "message" not in body
    assert body["ok"] == True

    # Cleanup
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })


def test_backend_validate_higher_total(payment_3p_api_url, payment_api_url, iam_auth):
    """
    Test /backend/validate with a higher total
    """

    card_number = "1234567890123456"
    total = 3000

    # Create a payment token
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": card_number,
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        auth=iam_auth(payment_api_url),
        json={
            "paymentToken": payment_token,
            "total": total+2000
        }
    )

    assert res.status_code == 200
    body = res.json()
    assert "ok" in body
    assert "message" not in body
    assert body["ok"] == False

    # Cleanup
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })


def test_backend_validate_no_iam(payment_3p_api_url, payment_api_url):
    """
    Test /backend/validate without IAM authorization
    """

    card_number = "1234567890123456"
    total = 3000

    # Create a payment token
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": card_number,
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        json={
            "paymentToken": payment_token,
            "total": total
        }
    )

    assert res.status_code == 403
    body = res.json()
    assert "ok" not in body
    assert "message" in body

    # Cleanup
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })


def test_backend_validate_no_total(payment_3p_api_url, payment_api_url, iam_auth):
    """
    Test /backend/validate without an total
    """

    card_number = "1234567890123456"
    total = 3000

    # Create a payment token
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": card_number,
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        auth=iam_auth(payment_api_url),
        json={
            "paymentToken": payment_token
        }
    )

    assert res.status_code == 400
    body = res.json()
    assert "ok" not in body
    assert "message" in body
    assert "total" in body["message"]

    # Cleanup
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })


def test_backend_validate_no_payment_token(payment_3p_api_url, payment_api_url, iam_auth):
    """
    Test /backend/validate without a payment token
    """

    card_number = "1234567890123456"
    total = 3000

    # Create a payment token
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": card_number,
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Validate the token
    res = requests.post(
        payment_api_url+"/backend/validate",
        auth=iam_auth(payment_api_url),
        json={
            "total": total
        }
    )

    assert res.status_code == 400
    body = res.json()
    assert "ok" not in body
    assert "message" in body
    assert "paymentToken" in body["message"]

    # Cleanup cancelPayment
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })