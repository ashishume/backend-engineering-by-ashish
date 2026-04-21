import CommentsTableClient from "./components/comments-table-client";


type Comment = {
  id: number;
  name: string;
  body: string;
};

async function fetchData(): Promise<Comment[]> {
  const response = await fetch(
    "https://jsonplaceholder.typicode.com/comments",
    { cache: "no-store" }
  );

  const resp = response.json();
  return resp;
}

export default async function Home() {
  const data = await fetchData();

  return (
    <div className="flex flex-col gap-4 p-4">
      <CommentsTableClient items={data} />
    </div>
  );
}
