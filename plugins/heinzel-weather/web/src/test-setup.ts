import "@testing-library/jest-dom/vitest";
import {cleanup} from "@testing-library/react";
import {afterEach} from "vitest";
afterEach(cleanup);
const nothing = (): void => undefined;
class Observer { observe = nothing; unobserve = nothing; disconnect = nothing; }
globalThis.ResizeObserver ??= Observer as unknown as typeof ResizeObserver;
window.matchMedia ??= ((query: string) => ({ matches:false, media:query, onchange:null,
  addEventListener: nothing, removeEventListener: nothing, addListener: nothing, removeListener: nothing, dispatchEvent:()=>false
})) as unknown as typeof window.matchMedia;
