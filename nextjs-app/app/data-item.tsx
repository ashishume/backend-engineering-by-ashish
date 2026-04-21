'use client';

import { useRouter } from "next/navigation";

export default function DataItem({ item }: any) {

    const route=useRouter()
    const handleClick=()=>{
        route.push(`/comments/${item.id}`)
    }

    return <div key={item.id} onClick={handleClick}className="rounded-md border-2 border-gray-300 p-2">
        <h1 className="font-semibold">{item.name}</h1>
        <p>{item.body}</p>
    </div>
}