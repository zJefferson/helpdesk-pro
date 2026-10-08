import { zodResolver } from "@hookform/resolvers/zod";
import { Headset } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Field, inputClass } from "../components/ui";

const schema = z.object({
  email: z.string().trim().min(1, "Informe seu e-mail.").email("E-mail inválido."),
  password: z.string().min(1, "Informe sua senha."),
});
type FormData = z.infer<typeof schema>;

export function LoginPage() {
  const { state, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  if (state.status === "authenticated") return <Navigate to={from} replace />;

  const onSubmit = async (data: FormData) => {
    setServerError(null);
    try {
      await login(data.email, data.password);
      navigate(from, { replace: true });
    } catch (error) {
      setServerError(errorMessage(error));
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center bg-slate-50 px-4 py-12">
      <div className="mx-auto w-full max-w-sm">
        <div className="flex items-center justify-center gap-2.5">
          <span className="flex size-10 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Headset className="size-5" aria-hidden />
          </span>
          <span className="text-xl font-semibold tracking-tight text-slate-900">HelpDesk Pro</span>
        </div>
        <h1 className="mt-8 text-center text-lg font-semibold text-slate-900">Entre na sua conta</h1>
        <p className="mt-1 text-center text-sm text-slate-500">
          Acompanhe e resolva chamados de suporte de TI.
        </p>

        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className="mt-8 space-y-5 rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200"
        >
          {serverError && (
            <div role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {serverError}
            </div>
          )}
          <Field label="E-mail" htmlFor="email" error={errors.email?.message}>
            <input
              id="email"
              type="email"
              autoComplete="email"
              autoFocus
              className={inputClass}
              aria-invalid={!!errors.email}
              {...register("email")}
            />
          </Field>
          <Field label="Senha" htmlFor="password" error={errors.password?.message}>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className={inputClass}
              aria-invalid={!!errors.password}
              {...register("password")}
            />
          </Field>
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Entrar
          </Button>
        </form>
      </div>
    </div>
  );
}
