import './Header.css';

function Header() {
  return (
    <header className="header">
      {/* Left Section: Logo */}
      <div className="leftSection">
        <a href="/" className="logo">
          <h1>ReptileHub</h1>
        </a>
      </div>

      {/* Middle Section: Search Bar */}
      <div className="middleSection">
        <input 
          type="text" 
          placeholder="Search for reptiles..." 
          className="searchBar" 
        />
      </div>

      {/* Right Section: Buttons */}
      <div className="rightSection">
        <button className="headerButton">Upload</button>
        <button className="headerButton">Profile</button>
      </div>
    </header>
  );
}

export default Header;