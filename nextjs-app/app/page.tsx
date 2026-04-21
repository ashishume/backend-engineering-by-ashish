import DataItem from "./data-item";
import FilterButton from "./filter-button";

type Comment = {
  id: number;
  name: string;
  body: string;
};

async function fetchData(searchTerm = ""): Promise<Comment[]> {
  const response = await fetch(
    `https://jsonplaceholder.typicode.com/comments?q=${encodeURIComponent(searchTerm)}`,
    { cache: "no-store" }
  );
  return response.json();
}

type HomeProps = {
  searchParams?: Promise<{
    search?: string;
  }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const resolvedSearchParams = await searchParams;
  const searchTerm = resolvedSearchParams?.search ?? "";

  const data = await fetchData(searchTerm);
  return (
    <div className="flex flex-col gap-4 p-4">
      <FilterButton />

      {data.map((item) => <DataItem key={item.id} item={item} />)}
    </div>
  );
}
