import { createContext, useContext, type ReactNode } from 'react';
import { useIdentification } from './useIdentification';
const Context = createContext<ReturnType<typeof useIdentification> | null>(null);
export function ScanProvider({ children }: { children: ReactNode }) {
  const scan = useIdentification();
  return <Context.Provider value={scan}>{children}</Context.Provider>;
}
export function useScan() {
  const scan = useContext(Context); if (!scan) throw new Error('Scan provider missing'); return scan;
}
