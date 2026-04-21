'use client'
import { ChangeEvent } from "react";

type SearchBarProps = {
    value: string;
    onSearchChange: (value: string) => void;
};

const SearchBar = ({ value, onSearchChange }: SearchBarProps) => {

    const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value
        onSearchChange(val)
    }

    return <input value={value} placeholder="search..." onChange={handleChange} className="border p-2 rounded" />
}

export default SearchBar