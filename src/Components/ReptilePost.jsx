function ReptilePost({ props }) {
  // Destructuring with defaults for safety
  const {species, price, imageUrl, size} = props;
  return (
    <div className="reptilepost">
        <img 
          src={imageUrl} 
          alt={"image of " + species} 
        />
        <div className="postinfo">
        <h2 style={{ margin: 0, color: '#000000ff' }}>{species}</h2>
        {size}
        <p>${price}</p>
        </div>
    </div>
  );
};

export default ReptilePost;