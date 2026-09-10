'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { ApiError, formatApiErrorMessage, isCancelError } from '../lib/apiClient';

/**
 * Custom hook to execute API calls with full lifecycle management:
 * - Loading state (isLoading)
 * - Success state (isSuccess)
 * - Error state (isError, error, userMessage)
 * - Empty response state (isEmpty)
 * - Auto-cancellation on re-trigger or component unmount
 *
 * @param {Function} apiFunc - Async function that performs the API call (e.g. catalogService.getProducts)
 * @param {object} options - { initialData, immediate, params }
 */
export function useApi(apiFunc, options = {}) {
  const { initialData = null, immediate = false, params = [] } = options;

  const [data, setData] = useState(initialData);
  const [isLoading, setIsLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const [userMessage, setUserMessage] = useState(null);
  const [isSuccess, setIsSuccess] = useState(false);

  // Reference to track active in-flight AbortController
  const abortControllerRef = useRef(null);
  const isMountedRef = useRef(true);

  // Check if current data represents an empty response
  const isEmpty =
    !isLoading &&
    !error &&
    (data === null ||
      data === undefined ||
      (Array.isArray(data) && data.length === 0) ||
      (Array.isArray(data?.results) && data.results.length === 0) ||
      (typeof data === 'object' && Object.keys(data).length === 0));

  const execute = useCallback(
    async (...args) => {
      // Abort any prior in-flight request from this hook
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsLoading(true);
      setError(null);
      setUserMessage(null);
      setIsSuccess(false);

      try {
        // Pass signal as last argument or merge into options
        const result = await apiFunc(...args, { signal: controller.signal });

        if (isMountedRef.current) {
          setData(result);
          setIsSuccess(true);
          return result;
        }
      } catch (err) {
        // Ignore aborted errors
        if (isCancelError(err)) {
          return;
        }

        if (isMountedRef.current) {
          const apiErr =
            err instanceof ApiError
              ? err
              : new ApiError({
                  message: err.message,
                  status: err.status || 0,
                  raw: err,
                });

          setError(apiErr);
          setUserMessage(apiErr.userMessage || formatApiErrorMessage(apiErr));
          throw apiErr;
        }
      } finally {
        if (isMountedRef.current) {
          setIsLoading(false);
          abortControllerRef.current = null;
        }
      }
    },
    [apiFunc]
  );

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setData(initialData);
    setIsLoading(false);
    setError(null);
    setUserMessage(null);
    setIsSuccess(false);
  }, [initialData]);

  useEffect(() => {
    isMountedRef.current = true;
    if (immediate) {
      execute(...(Array.isArray(params) ? params : [params]));
    }
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [execute, immediate, params]);

  return {
    data,
    setData,
    isLoading,
    isSuccess,
    isError: Boolean(error),
    isEmpty,
    error,
    userMessage,
    execute,
    reset,
  };
}

export default useApi;
