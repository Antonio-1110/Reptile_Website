function ReptilePost({ props, onView }) {
  return (
    <div className="reptilepost">
      <img src={props.imageUrl} alt={props.species} />

      <div className="postinfo">
        <strong>{props.species}</strong>
        <span className="price">${props.price}</span>

        <button className="upload-btn" onClick={onView}>
          View Options
        </button>
      </div>
    </div>
  );
}

export default ReptilePost;
