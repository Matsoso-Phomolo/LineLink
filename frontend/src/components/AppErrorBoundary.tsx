import { Component, type ErrorInfo, type ReactNode } from "react";
import { tokenStorage } from "../auth/tokenStorage";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  resetSession = () => {
    tokenStorage.remove();
    window.location.href = "/#/login";
    window.location.reload();
  };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("LineLink UI error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="center-page">
          <section className="auth-card">
            <p className="eyebrow">LineLink</p>
            <h1>We could not load this screen</h1>
            <p>Refresh the page or return to the login screen. Your account data is still protected.</p>
            <button className="primary-button" type="button" onClick={this.resetSession}>Reset session and return to login</button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
