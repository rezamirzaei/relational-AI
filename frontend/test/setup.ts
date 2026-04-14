import "@testing-library/jest-dom/vitest";

/* ResizeObserver polyfill for recharts in jsdom */
const DEFAULT_ELEMENT_WIDTH = 640;
const DEFAULT_ELEMENT_HEIGHT = 240;

function parseDimension(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function measureElementDimension(element: HTMLElement, axis: "width" | "height"): number {
  const computedStyle = globalThis.getComputedStyle(element);
  const inlineValue = axis === "width" ? element.style.width : element.style.height;
  const computedValue = axis === "width" ? computedStyle.width : computedStyle.height;
  const minValue = axis === "width" ? computedStyle.minWidth : computedStyle.minHeight;

  return (
    parseDimension(inlineValue) ??
    parseDimension(computedValue) ??
    parseDimension(minValue) ??
    (axis === "width" ? DEFAULT_ELEMENT_WIDTH : DEFAULT_ELEMENT_HEIGHT)
  );
}

const originalGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect;

Object.defineProperties(HTMLElement.prototype, {
  clientWidth: {
    configurable: true,
    get(): number {
      return measureElementDimension(this as HTMLElement, "width");
    },
  },
  clientHeight: {
    configurable: true,
    get(): number {
      return measureElementDimension(this as HTMLElement, "height");
    },
  },
  offsetWidth: {
    configurable: true,
    get(): number {
      return measureElementDimension(this as HTMLElement, "width");
    },
  },
  offsetHeight: {
    configurable: true,
    get(): number {
      return measureElementDimension(this as HTMLElement, "height");
    },
  },
});

HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect(): DOMRect {
  const width = measureElementDimension(this, "width");
  const height = measureElementDimension(this, "height");

  if (width > 0 && height > 0) {
    return new DOMRect(0, 0, width, height);
  }

  return originalGetBoundingClientRect.call(this);
};

class ResizeObserverMock implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}

  observe(target: Element): void {
    const element = target as HTMLElement;
    const width = measureElementDimension(element, "width");
    const height = measureElementDimension(element, "height");
    const entry = {
      target,
      contentRect: new DOMRectReadOnly(0, 0, width, height),
      borderBoxSize: [],
      contentBoxSize: [],
      devicePixelContentBoxSize: [],
    } as ResizeObserverEntry;

    this.callback([entry], this);
  }

  unobserve(): void {}

  disconnect(): void {}
}

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = ResizeObserverMock;
}

class StorageMock implements Storage {
  private readonly values = new Map<string, string>();

  get length(): number {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

Object.defineProperty(window, "localStorage", {
  value: new StorageMock(),
  writable: true,
});
