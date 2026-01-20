import Navbar from "./Components/Navbar"
import SearchBar from "./Components/Searchbar"  
import FilterBox from "./Components/FilterBox"
import ReptilePost from "./Components/ReptilePost"
import musk from "./assets/musk.jpg"
function App() {
    const samplePet = {
        species: "屋頂龜",
        price: 100,
        imageUrl : musk,
        size : 10
    }
    return (
    <>
    <ReptilePost props={samplePet}/>
    </>
)
}

export default App