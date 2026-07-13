import { useEffect, useState } from 'react';

/**
 * Debounce a value — useful for search inputs.
 * Future: use across Leads, Activity filters.
 */
export default function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
