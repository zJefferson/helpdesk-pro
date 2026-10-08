from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.serializers import RejectReadOnlyFieldsMixin

from .models import Role, User, normalize_email


class LoginSerializer(TokenObtainPairSerializer):
    # Mensagem genérica de propósito: não revela se o e-mail existe ou se a senha está errada.
    default_error_messages = {"no_active_account": "E-mail ou senha inválidos."}


class UserSummarySerializer(serializers.ModelSerializer):
    """Versão resumida do usuário, usada dentro de outros recursos (ex.: chamados)."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "full_name", "email"]
        read_only_fields = fields


class MeSerializer(RejectReadOnlyFieldsMixin, serializers.ModelSerializer):
    """
    Dados do próprio usuário. Ele só pode alterar o nome.

    `role`, `email` e `is_active` são somente leitura: tentar enviá-los gera 400.
    Assim ninguém consegue se promover a administrador pela API.
    """

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "email", "role", "is_active", "date_joined"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Senha atual incorreta.")
        return value

    def validate_new_password(self, value):
        # Aplica os mesmos validadores de força de senha configurados no settings.
        validate_password(value, user=self.context["request"].user)
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError("Token inválido ou expirado.") from exc

        # Um usuário não pode invalidar o token de outra pessoa.
        user = self.context["request"].user
        if str(token.get("user_id")) != str(user.pk):
            raise serializers.ValidationError("Este token não pertence ao usuário autenticado.")

        self.token = token
        return value

    def save(self):
        self.token.blacklist()


class UserSerializer(RejectReadOnlyFieldsMixin, serializers.ModelSerializer):
    """Gestão de usuários pelo administrador."""

    password = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "password",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]
        # A unicidade do e-mail é validada em `validate_email` (sem diferenciar maiúsculas).
        extra_kwargs = {"email": {"validators": []}}

    def validate_email(self, value):
        email = normalize_email(value)
        others = User.objects.filter(email__iexact=email)
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError("Já existe um usuário com este e-mail.")
        return email

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request_user = self.context["request"].user

        if self.instance is None:
            password = attrs.get("password")
            if not password:
                raise serializers.ValidationError({"password": "Este campo é obrigatório."})
            # Valida a força da senha considerando os dados do novo usuário.
            candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
            try:
                validate_password(password, user=candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        else:
            if "password" in attrs:
                raise serializers.ValidationError(
                    {"password": "A senha não pode ser alterada por este endpoint."}
                )
            # RN21: o admin não pode se rebaixar nem se desativar (evita ficar sem admin).
            if self.instance.pk == request_user.pk:
                if attrs.get("role", Role.ADMIN) != Role.ADMIN:
                    raise serializers.ValidationError(
                        {"role": "Você não pode remover o seu próprio perfil de administrador."}
                    )
                if attrs.get("is_active") is False:
                    raise serializers.ValidationError(
                        {"is_active": "Você não pode desativar a sua própria conta."}
                    )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)
