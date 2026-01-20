import FilterBox from "./Components/FilterBox"
import PostViewing from "./Components/PostViewing"
import { useState } from "react"
function App() {
    const [filters, setFilters] = useState({
    location: "",
    minPrice: 0,
    maxPrice: 1000,
    minSize: 0,
    maxSize: 200,
    })
    return (
    <>
    <div className="layout">
    <FilterBox filters={filters} setFilters={setFilters}/>
    <PostViewing />
    </div>
    </>
)
}

export default App