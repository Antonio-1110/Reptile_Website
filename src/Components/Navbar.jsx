import reactLogo from '../assets/react.svg'

function Navbar(){
    return(
        <header>
            <nav className='navbar'>
                <img src={reactLogo} alt="React logo" />
                <h1>React Facts</h1>
            </nav>
        </header>
    )
}

export default Navbar