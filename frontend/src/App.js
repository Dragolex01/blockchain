import "./App.css";
import { Transactions } from "./components/Transactions";
import { Balance } from "./components/Balance";
import { Price } from "./components/Price";

function App() {
  return (
    <div>
      <header>
        <h1>Piñacoin</h1>
      </header>
      <main>
        <section>
          <Balance />
          <Transactions />
          {/* <Price /> */}
        </section>
      </main>
    </div>
  );
}

export default App;
