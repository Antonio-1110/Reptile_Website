import { useState } from "react";
import Searchbar from "./Components/Searchbar";
import FilterBox from "./Components/FilterBox";
import ReptilePost from "./Components/ReptilePost";
import UploadModal from "./Components/UploadModal";
import ReptileDetailModal from "./Components/ReptileDetailModal";

import musk from "./assets/musk.jpg";

function App() {
  const [query, setQuery] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [selectedPet, setSelectedPet] = useState(null);

  const pets = [
    { species: "屋頂龜", price: 100, size: "Small", imageUrl: musk },
    { species: "球蟒", price: 320, size: "Large", imageUrl: musk },
    { species: "豹紋守宮", price: 220, size: "Medium", imageUrl: musk },
    { species: "綠鬣蜥", price: 450, size: "Large", imageUrl: musk },
    { species: "紅耳龜", price: 180, size: "Small", imageUrl: musk },
  ];

  const filteredPets = pets.filter((pet) =>
    pet.species.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <>
      {/* TOP BAR */}
      <div className="reptilefloat-topbar">
        <div className="reptilefloat-search-wrap">
          <div style={{ flex: 1 }}>
            <Searchbar onSearch={setQuery} />
          </div>
          <button className="upload-btn" onClick={() => setShowUpload(true)}>
            + List Reptile
          </button>
        </div>
      </div>

      {/* MARKET */}
      <div className="market-container">
        <FilterBox />
        <div className="grid">
          {filteredPets.map((pet, i) => (
            <ReptilePost
              key={i}
              props={pet}
              onView={() => setSelectedPet(pet)}
            />
          ))}
        </div>
      </div>

      {/* MODALS */}
      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
      {selectedPet && (
        <ReptileDetailModal
          pet={selectedPet}
          onClose={() => setSelectedPet(null)}
        />
      )}
    </>
  );
}

export default App;
