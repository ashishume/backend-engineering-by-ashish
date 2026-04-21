type CommentPageProps = {
  params: Promise<{ id: string }>;
};

export default async function Page({ params }: CommentPageProps) {
  const { id } = await params;
  return <div>ID: {id}</div>;
}
