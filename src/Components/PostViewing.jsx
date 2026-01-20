import musk from "../assets/musk.jpg"
import ReptilePost from "./ReptilePost"
export default function PostViewing() {
    const samplePet = {
            species: "屋頂龜",
            price: 100,
            imageUrl : musk,
            size : 10
    }
    return (
    <div className="post-grid">
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
        <ReptilePost props={samplePet}/>
    </div>
  );
}