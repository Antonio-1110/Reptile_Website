import musk from "../../assets/musk.jpg"
import wt from "../../assets/wt.jpeg"
import ReptilePost from "./ReptilePost"
export default function PostViewing() {
    const samplePet1 = {
            species: "屋頂龜",
            price: 100,
            imageUrl : musk,
            size : 10
    }
    const samplePet2 = {
            species: "西瓜龜",
            price: 200,
            imageUrl : wt,
            size : 15
    }
    return (
    <div className="post-grid">
        <ReptilePost props={samplePet1}/>
        <ReptilePost props={samplePet2}/>
        <ReptilePost props={samplePet1}/>
        <ReptilePost props={samplePet2}/>
        <ReptilePost props={samplePet1}/>
        <ReptilePost props={samplePet1}/>
        <ReptilePost props={samplePet1}/>
        <ReptilePost props={samplePet2}/>
        <ReptilePost props={samplePet1}/>
        <ReptilePost props={samplePet2}/>
        <ReptilePost props={samplePet2}/>
        <ReptilePost props={samplePet1}/>
    </div>
  );
}