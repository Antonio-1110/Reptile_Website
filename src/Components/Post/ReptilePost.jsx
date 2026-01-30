import './ReptilePost.css';

function ReptilePost({ props }) {
  // Destructuring with defaults for safety
  const {species, price, imageUrl, size} = props;
  return (
    <div className="reptilepost">
      <img src={imageUrl} alt={`image of ${species}`} />
      <div className="post-info">
        <div className="post-info-box">
          <h2>{species}</h2>
          <h3>${price}</h3>
        </div>
        <div className="post-info-box">
          <span style={{fontSize : "1.1rem", fontWeight: "800"}}>{size}cm</span>
          <span style={{fontSize : "0.75rem"}}>${(price / size).toFixed(2)}/cm</span>
        </div>
      </div>
    </div>
  );
};

export default ReptilePost;