import Filter from "./Components/Filter/FilterBox"
import Post from "./Components/Post/PostWindow"
import Header from "./Components/Header/Header"
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
        <Header/>
        <div className="layout">
            <Filter filters={filters} setFilters={setFilters}/>
            <Post/>
        </div>
    </>
)
}
export default App