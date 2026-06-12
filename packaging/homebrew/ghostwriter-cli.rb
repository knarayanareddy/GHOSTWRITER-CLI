class GhostwriterCli < Formula
  include Language::Python::Virtualenv

  desc "Local-first, privacy-preserving AI writing assistant powered by Ollama"
  homepage "https://github.com/knarayanareddy/GHOSTWRITER-CLI"
  url "https://files.pythonhosted.org/packages/source/g/ghostwriter-cli/ghostwriter-cli-1.0.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SDIST_SHA256"
  license "MIT"

  depends_on "python@3.12"
  depends_on "ollama" => :recommended

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "ghostwriter", shell_output("#{bin}/ghostwriter --version")
    assert_match "ghostwriter_version", shell_output("#{bin}/ghostwriter doctor --json")
  end
end
