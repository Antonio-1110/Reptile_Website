export default function UploadModal({ onClose }) {
  function handleSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const data = {
      species: form.species.value,
      price: form.price.value,
      size: form.size.value,
      image: form.image.files[0],
    };

    console.log("Uploaded item:", data);
    alert("Item submitted (check console)");

    onClose();
  }

  return (
    <div className="modal-backdrop">
      <form className="modal" onSubmit={handleSubmit}>
        <h2>List a Reptile</h2>

        <label>Species</label>
        <input name="species" required />

        <label>Price</label>
        <input name="price" type="number" required />

        <label>Size</label>
        <select name="size">
          <option>Small</option>
          <option>Medium</option>
          <option>Large</option>
        </select>

        <label>Image</label>
        <input name="image" type="file" accept="image/*" required />

        <div className="modal-actions">
          <button type="button" className="cancel-btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="submit-btn">
            Upload
          </button>
        </div>
      </form>
    </div>
  );
}
