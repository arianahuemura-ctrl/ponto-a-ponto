import { Component } from "react";

// Uma atualização pode remover um módulo que uma aba antiga ainda tenta abrir.
// Ofereça recuperação sem apagar favoritos, consentimento ou o parâmetro do QR.
export default class AppBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main role="alert" style={{ maxWidth: "32rem", margin: "3rem auto", padding: "1.5rem", font: "1rem/1.5 system-ui", color: "#13263b", background: "#fff", borderRadius: "1rem" }}>
        <h1>Não foi possível abrir o PaP</h1>
        <p>Confira sua conexão e tente recarregar a página. Seus favoritos serão preservados.</p>
        <button type="button" onClick={() => {
          const url = new URL(window.location.href);
          url.searchParams.set("_pap_reload", String(Date.now()));
          window.location.replace(url.href);
        }}>Recarregar aplicativo</button>
      </main>
    );
  }
}
