'use client';

import { useEffect, useMemo, useState } from "react";
import DataTable from "./data-table";
import SearchBar from "./search-bar";

type Comment = {
  id: number;
  name: string;
  body: string;
};

type CommentsTableClientProps = {
  items: Comment[];
};

export default function CommentsTableClient({ items }: CommentsTableClientProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState<Comment[]>(items);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    const trimmedSearchTerm = searchTerm.trim();
    const controller = new AbortController();
    const timeoutId = setTimeout(async () => {
      if (!trimmedSearchTerm) {
        setResults(items);
        setCurrentPage(1);
        return;
      }

      setIsLoading(true);
      try {
        const response = await fetch(
          `https://jsonplaceholder.typicode.com/comments?q=${encodeURIComponent(trimmedSearchTerm)}`,
          { signal: controller.signal }
        );
        const data: Comment[] = await response.json();
        setResults(data);
        setCurrentPage(1);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setResults([]);
          setCurrentPage(1);
        }
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [items, searchTerm]);

  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(results.length / pageSize));
  }, [results.length]);

  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return results.slice(start, start + pageSize);
  }, [currentPage, results]);

  const goToPreviousPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  };

  return (
    <>
      <SearchBar value={searchTerm} onSearchChange={setSearchTerm} />
      {isLoading ? <p>Loading...</p> : <DataTable items={paginatedItems} />}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={goToPreviousPage}
          disabled={currentPage === 1}
          className="rounded border px-3 py-1 disabled:opacity-50"
        >
          Prev
        </button>
        <p>
          Page {currentPage} of {totalPages}
        </p>
        <button
          type="button"
          onClick={goToNextPage}
          disabled={currentPage === totalPages}
          className="rounded border px-3 py-1 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </>
  );
}
