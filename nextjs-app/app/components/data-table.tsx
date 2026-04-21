'use client'
type Comment = {
    id: number;
    name: string;
    body: string;
};

type DataTableProps = {
    items: Comment[];
};

const DataTable = ({ items }: DataTableProps) => {

    return <table style={{
        border:"solid 1px black",
        borderCollapse: "collapse"
    }}>

        <thead>
            <tr>
                <td>Id</td>
                <td>Name</td>
                <td>Body</td>
            </tr>
        </thead>
        <tbody style={{
            border:"solid 1px black",
        }}>
            {
                items.map((value) => {
                    return <tr key={value.id} style={{
                        border:"solid 1px black",
                    }}>
                        <td>{value.id}</td>
                        <td>{value.name}</td>
                        <td>{value.body}</td>
                    </tr>
                })
            }
        </tbody>
    </table>
}

export default DataTable