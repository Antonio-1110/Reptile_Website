import { useState } from "react";

function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("");

  const handleChange = (e) => {
    setQuery(e.target.value);
  };

  const handleSearch = () => {
    onSearch(query);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") onSearch(query);
  };

  return (
    <div className="flex items-center w-full max-w-md mx-auto mt-4 border border-gray-300 rounded-2xl overflow-hidden">
      <input
        type="text"
        value={query}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Search..."
        className="flex-grow px-4 py-2 outline-none"
      />
      <button
        onClick={handleSearch}
        className="px-4 py-2 bg-blue-500 text-white hover:bg-blue-600"
      >
      </button>
    </div>
  );
}

export default SearchBar;