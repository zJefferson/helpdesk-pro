import { useEffect, useState } from "react";

/** Devolve `value` só depois que ele parar de mudar por `delay` ms (evita uma busca por tecla). */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
