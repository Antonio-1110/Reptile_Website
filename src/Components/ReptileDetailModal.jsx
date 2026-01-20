function ReptileDetailModal({ pet, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{pet.species}</h2>
        <p className="price">${pet.price}</p>

        <div className="action-column">
          <button className="buy-btn">Buy Now</button>
          <button className="cart-btn">Add to Cart</button>
          <button className="bargain-btn">Bargain</button>
        </div>

        <button className="cancel-btn" onClick={onClose}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default ReptileDetailModal;
