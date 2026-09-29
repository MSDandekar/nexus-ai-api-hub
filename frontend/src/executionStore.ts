import { useSyncExternalStore, useCallback, useEffect } from 'react';

/**
 * AI Nexus — Generic Playground State & Execution Architecture
 * 
 * Strict State Separation:
 * 1. Connector configuration (server metadata, inputs definition)
 * 2. User input state (formValues, files, imagePreviews, hasUserEdited flag)
 * 3. Execution state (isExecuting / loading)
 * 4. Last execution result (persistent across rerenders, polling, and input changes)
 * 5. Execution error (persists alongside or as execution result)
 * 6. Background metrics state (completely isolated in App / Dashboard)
 * 
 * Invariants:
 * - Once user enters a value into an input field, it persists indefinitely until the user edits it.
 * - Server refreshes and background polling NEVER overwrite user-edited form values.
 * - Starting a new execution does NOT clear the previous result while in-flight.
 * - Last execution result changes ONLY when a new execution finishes or the user clicks "Clear Output".
 * - Fully generic across all existing and dynamic connectors (keyed by connector slug).
 */

export interface ConnectorSession {
  formValues: Record<string, any>;
  files: Record<string, File>;
  imagePreviews: Record<string, string>;
  lastResult: any | null;
  executionError: string | null;
  isExecuting: boolean;
  hasUserEdited: boolean;
}

export const DEFAULT_SESSION: ConnectorSession = Object.freeze({
  formValues: Object.freeze({}),
  files: Object.freeze({}),
  imagePreviews: Object.freeze({}),
  lastResult: null,
  executionError: null,
  isExecuting: false,
  hasUserEdited: false,
});

// In-memory persistent session storage keyed by connector slug
const sessionStore: Record<string, ConnectorSession> = {};

type Listener = () => void;
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch (e) {
      console.error("Error in executionStore listener:", e);
    }
  });
}

export function getSession(slug: string | undefined): ConnectorSession {
  if (!slug) return DEFAULT_SESSION;
  return sessionStore[slug] || DEFAULT_SESSION;
}

/**
 * Initializes or updates connector form defaults safely.
 * Invariant: If user has already entered text or touched the form, existing values are NEVER overwritten.
 */
export function initSessionDefaults(connector: any): void {
  const slug = connector?.slug;
  if (!slug) return;

  const existing = sessionStore[slug];
  const inputs = connector?.inputs || [];

  if (!existing) {
    // Brand new session: compute initial defaults
    const initialValues: Record<string, any> = {};
    for (const inp of inputs) {
      if (inp.default_value !== null && inp.default_value !== undefined) {
        initialValues[inp.name] = inp.default_value;
      } else if (inp.type === "boolean") {
        initialValues[inp.name] = false;
      } else if (inp.type === "number") {
        initialValues[inp.name] = 0;
      } else if (inp.type === "json") {
        initialValues[inp.name] = "{}";
      } else {
        initialValues[inp.name] = "";
      }
    }

    sessionStore[slug] = {
      formValues: initialValues,
      files: {},
      imagePreviews: {},
      lastResult: null,
      executionError: null,
      isExecuting: false,
      hasUserEdited: false,
    };
    notify();
  } else {
    // Existing session: server data was refreshed.
    // Check if new inputs exist on server that are missing from current formValues
    let hasNewField = false;
    const mergedValues = { ...existing.formValues };

    for (const inp of inputs) {
      if (mergedValues[inp.name] === undefined) {
        hasNewField = true;
        if (inp.default_value !== null && inp.default_value !== undefined) {
          mergedValues[inp.name] = inp.default_value;
        } else if (inp.type === "boolean") {
          mergedValues[inp.name] = false;
        } else if (inp.type === "number") {
          mergedValues[inp.name] = 0;
        } else if (inp.type === "json") {
          mergedValues[inp.name] = "{}";
        } else {
          mergedValues[inp.name] = "";
        }
      }
    }

    if (hasNewField) {
      sessionStore[slug] = {
        ...existing,
        formValues: mergedValues,
      };
      notify();
    }
  }
}

/**
 * Updates form value directly from user input.
 * Invariant: Input edits NEVER modify lastResult or executionError.
 */
export function setInputValue(slug: string, fieldName: string, value: any): void {
  if (!slug) return;
  const current = sessionStore[slug] || {
    ...DEFAULT_SESSION,
    formValues: {},
  };

  sessionStore[slug] = {
    ...current,
    formValues: {
      ...current.formValues,
      [fieldName]: value,
    },
    hasUserEdited: true,
  };
  notify();
}

/**
 * Updates uploaded file inputs and image previews.
 */
export function setFormFile(slug: string, fieldName: string, file: File | null): void {
  if (!slug) return;
  const current = sessionStore[slug] || {
    ...DEFAULT_SESSION,
    files: {},
    imagePreviews: {},
  };

  const newFiles = { ...current.files };
  const newPreviews = { ...current.imagePreviews };

  if (file) {
    newFiles[fieldName] = file;
    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const previewUrl = e.target?.result as string;
        if (sessionStore[slug]) {
          sessionStore[slug] = {
            ...sessionStore[slug],
            imagePreviews: {
              ...sessionStore[slug].imagePreviews,
              [fieldName]: previewUrl,
            },
          };
          notify();
        }
      };
      reader.readAsDataURL(file);
    }
  } else {
    delete newFiles[fieldName];
    delete newPreviews[fieldName];
  }

  sessionStore[slug] = {
    ...current,
    files: newFiles,
    imagePreviews: newPreviews,
    hasUserEdited: true,
  };
  notify();
}

/**
 * Initiates execution.
 * Invariant: Preserves previous lastResult on screen during in-flight request.
 */
export function startExecution(slug: string): void {
  if (!slug) return;
  const current = sessionStore[slug] || DEFAULT_SESSION;
  sessionStore[slug] = {
    ...current,
    isExecuting: true,
    // Keep previous lastResult visible during in-flight request
  };
  notify();
}

/**
 * Replaces the execution result upon success.
 */
export function setExecutionSuccess(slug: string, result: any): void {
  if (!slug) return;
  const current = sessionStore[slug] || DEFAULT_SESSION;
  sessionStore[slug] = {
    ...current,
    lastResult: result,
    executionError: null,
    isExecuting: false,
  };
  notify();
}

/**
 * Updates execution result / error upon failure.
 */
export function setExecutionError(slug: string, error: string, result?: any): void {
  if (!slug) return;
  const current = sessionStore[slug] || DEFAULT_SESSION;
  sessionStore[slug] = {
    ...current,
    lastResult: result !== undefined ? result : current.lastResult,
    executionError: error,
    isExecuting: false,
  };
  notify();
}

/**
 * Explicit user action to clear the output.
 */
export function clearOutput(slug: string): void {
  if (!slug) return;
  const current = sessionStore[slug] || DEFAULT_SESSION;
  sessionStore[slug] = {
    ...current,
    lastResult: null,
    executionError: null,
    isExecuting: false,
  };
  notify();
}

/**
 * Custom React hook subscribing to a connector's isolated session.
 */
export function useConnectorSession(connector: any) {
  const slug = connector?.slug;

  const subscribe = useCallback((onStoreChange: () => void) => {
    listeners.add(onStoreChange);
    return () => {
      listeners.delete(onStoreChange);
    };
  }, []);

  const getSnapshot = useCallback(() => {
    return getSession(slug);
  }, [slug]);

  const session = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  // Initialize or safely update defaults on mount or when server definition refreshes
  useEffect(() => {
    if (connector?.slug && connector?.inputs) {
      initSessionDefaults(connector);
    }
  }, [connector?.slug, connector?.inputs]);

  const setInput = useCallback((fieldName: string, value: any) => {
    if (!slug) return;
    setInputValue(slug, fieldName, value);
  }, [slug]);

  const setFile = useCallback((fieldName: string, file: File | null) => {
    if (!slug) return;
    setFormFile(slug, fieldName, file);
  }, [slug]);

  return {
    formValues: session.formValues,
    files: session.files,
    imagePreviews: session.imagePreviews,
    lastResult: session.lastResult,
    executionError: session.executionError,
    isExecuting: session.isExecuting,
    setInput,
    setFile,
    startExecution: () => slug && startExecution(slug),
    setExecutionSuccess: (result: any) => slug && setExecutionSuccess(slug, result),
    setExecutionError: (error: string, result?: any) => slug && setExecutionError(slug, error, result),
    clearOutput: () => slug && clearOutput(slug),
  };
}

/**
 * Backwards-compatible aliases for legacy callers and tests
 */
export function getExecutionState(slug: string | undefined) {
  const session = getSession(slug);
  return {
    result: session.lastResult,
    error: session.executionError,
    loading: session.isExecuting,
  };
}

export function getFormState(slug: string | undefined) {
  const session = getSession(slug);
  return {
    values: session.formValues,
    files: session.files,
    imagePreviews: session.imagePreviews,
  };
}

export const clearExecution = clearOutput;
export const setFormValue = setInputValue;
export function ensureFormDefaults(slug: string, inputs: any[]): void {
  initSessionDefaults({ slug, inputs });
}
