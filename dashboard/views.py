from django.shortcuts import render


def index(request):
    return render(
        request,
        "dashboard/index.html",
        {
            "page_title": "AI POS Reconciliation Assistant",
            "supported_inputs": [
                "POS daily sales",
                "Card and bank deposits",
                "WooCommerce orders",
                "Fuel invoices",
                "Lottery settlements",
            ],
        },
    )

