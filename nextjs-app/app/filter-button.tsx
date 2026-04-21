"use client";

import { useRouter, useSearchParams } from "next/navigation";

export default function FilterButton() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleClick = (): void => {
  };

  return (
    <button
      onClick={handleClick}
      className="w-fit rounded-md bg-black px-4 py-2 text-white"
    >
      Filter results
    </button>
  );
}
