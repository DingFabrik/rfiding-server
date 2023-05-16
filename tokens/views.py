from django.views.generic.list import ListView

from tokens.models import Token

class TokenListView(ListView):
    model = Token
