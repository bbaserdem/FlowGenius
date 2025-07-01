{
  description = "FlowGenius: AI assisted learning assistant";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
    ...
  }: let
    inherit (nixpkgs) lib;

    # This example is only using x86_64-linux
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
    inherit (pkgs) stdenv;

    # Use Python 3.13 from nixpkgs
    python = pkgs.python313;

    baseSet = pkgs.callPackage pyproject-nix.build.packages {inherit python;};

    # Load a uv workspace from a workspace root.
    # Uv2nix treats all uv projects as workspace projects.
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};

    # Create package overlay from workspace.
    overlay = workspace.mkPyprojectOverlay {
      # Prefer prebuilt binary wheels as a package source.
      sourcePreference = "wheel";
    };

    # Extend generated overlay with build fixups
    #
    # Uv2nix can only work with what it has, and uv.lock is missing essential metadata to perform some builds.
    # This is an additional overlay implementing build fixups.
    # See:
    # - https://pyproject-nix.github.io/uv2nix/FAQ.html
    pyprojectOverrides = final: prev: {
      # Implement build fixups here.
      # Note that uv2nix is _not_ using Nixpkgs buildPythonPackage.
      # It's using https://pyproject-nix.github.io/pyproject.nix/build.html
      flowgenius = prev.flowgenius.overrideAttrs (old: {
        passthru =
          old.passthru
          // {
            # Put all tests in the passthru.tests attribute set.
            # Nixpkgs also uses the passthru.tests mechanism for ofborg test discovery.
            #
            # For usage with Flakes we will refer to the passthru.tests attributes
            # to construct the flake checks attribute set.
            tests = let
              virtualenv = final.mkVirtualEnv "flowgenius-pytest-env" {
                flowgenius = ["test"];
              };
            in
              (old.tests or {})
              // {
                pytest = stdenv.mkDerivation {
                  name = "${final.flowgenius.name}-pytest";
                  inherit (final.flowgenius) src;
                  nativeBuildInputs = [
                    virtualenv
                  ];
                  dontConfigure = true;

                  # Because this package is running tests, and not actually building the main package
                  # the build phase is running the tests.
                  #
                  # In this particular example we also output a HTML coverage report, which is used as the build output.
                  buildPhase = ''
                    runHook preBuild
                    pytest --cov tests --cov-report html
                    runHook postBuild
                  '';

                  # Install the HTML coverage report into the build output.
                  #
                  # If you wanted to install multiple test output formats such as TAP outputs
                  # you could make this derivation a multiple-output derivation.
                  #
                  # See https://nixos.org/manual/nixpkgs/stable/#chap-multiple-output for more information on multiple outputs.
                  installPhase = ''
                    runHook preInstall
                    mv htmlcov $out
                    runHook postInstall
                  '';
                };
              };
          };
      });
    };

    # Construct package set
    pythonSet = baseSet.overrideScope (
      lib.composeManyExtensions [
        pyproject-build-systems.overlays.default
        overlay
        pyprojectOverrides
      ]
    );
  in {
    # Package a virtual environment as our main application.
    #
    # Enable no optional dependencies for production build.
    packages.x86_64-linux.default = pythonSet.mkVirtualEnv "flowgenius-env" workspace.deps.default;

    # Make hello runnable with `nix run`
    apps.x86_64-linux = {
      default = {
        type = "app";
        program = "${self.packages.x86_64-linux.default}/bin/hello";
      };
    };

    # Make check available through nix flake check
    checks.x86_64-linux = {
      inherit (pythonSet.flowgenius.passthru.tests) pytest;
    };

    # This example provides two different modes of development:
    # - Impurely using uv to manage virtual environments
    # - Pure development using uv2nix to manage virtual environments
    devShells.x86_64-linux = {
      # This devShell uses uv2nix to construct a virtual environment purely from Nix, using the same dependency specification as the application.
      # The notable difference is that we also apply another overlay here enabling editable mode ( https://setuptools.pypa.io/en/latest/userguide/development_mode.html ).
      #
      # This means that any changes done to your local files do not require a rebuild.
      #
      # Note: Editable package support is still unstable and subject to change.
      default = let
        # Create an overlay enabling editable mode for all local dependencies.
        editableOverlay = workspace.mkEditablePyprojectOverlay {
          # Use environment variable
          root = "$REPO_ROOT";
          # Optional: Only enable editable for these packages
          # members = [ "flowgenius" ];
        };

        # Override previous set with our overrideable overlay.
        editablePythonSet = pythonSet.overrideScope (
          lib.composeManyExtensions [
            editableOverlay

            # Apply fixups for building an editable package of your workspace packages
            (final: prev: {
              flowgenius = prev.flowgenius.overrideAttrs (old: {
                # It's a good idea to filter the sources going into an editable build
                # so the editable package doesn't have to be rebuilt on every change.
                src = lib.fileset.toSource {
                  root = old.src;
                  fileset = lib.fileset.unions [
                    (old.src + "/pyproject.toml")
                    (old.src + "/README.md")
                    (old.src + "/src/flowgenius/__init__.py")
                  ];
                };

                # Hatchling (our build system) has a dependency on the `editables` package when building editables.
                #
                # In normal Python flows this dependency is dynamically handled, and doesn't need to be explicitly declared.
                # This behaviour is documented in PEP-660.
                #
                # With Nix the dependency needs to be explicitly declared.
                nativeBuildInputs =
                  old.nativeBuildInputs
                  ++ final.resolveBuildSystem {
                    editables = [];
                  };
              });
            })
          ]
        );

        # Build virtual environment, with local packages being editable.
        #
        # Enable all optional dependencies for development.
        virtualenv = editablePythonSet.mkVirtualEnv "flowgenius-dev-env" workspace.deps.all;
      in
        pkgs.mkShell {
          packages =
            [
              # Python packages
              virtualenv
              pkgs.uv
            ]
            ++ (with pkgs; [
              # Unix utilities
              coreutils # Basic file, shell and text manipulation utilities
              findutils # Find, locate, and xargs commands
              gnugrep # GNU grep, egrep and fgrep
              gnused # GNU stream editor
              ripgrep # Fast line-oriented search tool
              fd # Simple, fast and user-friendly alternative to find
              bat # Cat clone with syntax highlighting
              eza # Modern replacement for ls
              htop # Interactive process viewer
              jq # Lightweight JSON processor
              watch # Execute a program periodically
              curl # Command line tool for transferring data
              wget # Internet file retriever
              tree # Display directories as trees
              unzip # Unzip utility
              zip # Zip utility
              # External packages
              task-master-ai
            ]);

          env = {
            # Don't create venv using uv
            UV_NO_SYNC = "1";

            # Force uv to use Python interpreter from venv
            UV_PYTHON = python.interpreter;

            # Prevent uv from downloading managed Python's
            UV_PYTHON_DOWNLOADS = "never";
          };

          shellHook = ''
            # Undo dependency propagation by nixpkgs.
            unset PYTHONPATH

            # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
            export REPO_ROOT=$(git rev-parse --show-toplevel)
          '';
        };
    };
  };
}
