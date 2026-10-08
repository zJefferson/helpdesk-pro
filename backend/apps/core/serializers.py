from rest_framework import serializers


class RejectReadOnlyFieldsMixin:
    """
    Recusa (400) campos enviados que o cliente não pode alterar.

    Por padrão, o DRF simplesmente IGNORA campos read-only ou desconhecidos. Isso é seguro,
    mas silencioso: quem envia `{"role": "ADMIN"}` recebe 200 e acha que funcionou.
    Recusar explicitamente deixa a regra clara e fácil de testar.
    """

    def validate(self, attrs):
        writable = {name for name, field in self.fields.items() if not field.read_only}
        sent = set(getattr(self, "initial_data", {}) or {})
        forbidden = sorted(sent - writable)
        if forbidden:
            raise serializers.ValidationError(
                {name: "Este campo não pode ser alterado." for name in forbidden}
            )
        return super().validate(attrs)
