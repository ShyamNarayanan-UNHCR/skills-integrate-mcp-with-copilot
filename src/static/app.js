document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupMessage = document.getElementById("message");
  const teacherRequired = document.getElementById("teacher-required");
  const accountButton = document.getElementById("account-button");
  const accountMenu = document.getElementById("account-menu");
  const accountLabel = document.getElementById("account-label");
  const loginOpenButton = document.getElementById("login-open");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;
  let currentUsername = null;
  let messageTimer;

  function displayMessage(element, message, type) {
    element.textContent = message;
    element.className = `message ${type}`;
    element.classList.remove("hidden");

    if (element === signupMessage) {
      clearTimeout(messageTimer);
      messageTimer = setTimeout(() => {
        element.classList.add("hidden");
      }, 5000);
    }
  }

  function updateAuthUI() {
    accountLabel.textContent = isTeacher
      ? `Signed in as ${currentUsername}`
      : "Not signed in";
    loginOpenButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    signupForm.classList.toggle("hidden", !isTeacher);
    teacherRequired.classList.toggle("hidden", isTeacher);
  }

  async function refreshAuthState() {
    const response = await fetch("/auth/session");
    if (!response.ok) {
      throw new Error("Unable to check teacher sign-in status.");
    }

    const session = await response.json();
    isTeacher = session.authenticated;
    currentUsername = session.username;
    updateAuthUI();
  }

  function addText(parent, tagName, text, className) {
    const element = document.createElement(tagName);
    element.textContent = text;
    if (className) {
      element.className = className;
    }
    parent.appendChild(element);
    return element;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Activity request failed.");
      }
      const activities = await response.json();

      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const participants = details.participants;
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        addText(activityCard, "h4", name);
        addText(activityCard, "p", details.description);
        const schedule = addText(activityCard, "p", "");
        const scheduleLabel = document.createElement("strong");
        scheduleLabel.textContent = "Schedule: ";
        schedule.append(scheduleLabel, details.schedule);

        const spotsLeft = details.max_participants - participants.length;
        const availability = addText(activityCard, "p", "");
        const availabilityLabel = document.createElement("strong");
        availabilityLabel.textContent = "Availability: ";
        availability.append(availabilityLabel, `${spotsLeft} spots left`);

        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        if (participants.length > 0) {
          const participantsSection = document.createElement("div");
          participantsSection.className = "participants-section";
          addText(participantsSection, "h5", "Participants:");
          const participantsListElement = document.createElement("ul");
          participantsListElement.className = "participants-list";

          participants.forEach((email) => {
            const listItem = document.createElement("li");
            const participantEmail = addText(
              listItem,
              "span",
              email,
              "participant-email"
            );
            participantEmail.title = email;

            if (isTeacher) {
              const removeButton = document.createElement("button");
              removeButton.className = "delete-btn";
              removeButton.type = "button";
              removeButton.textContent = "❌";
              removeButton.setAttribute("aria-label", `Unregister ${email}`);
              removeButton.dataset.activity = name;
              removeButton.dataset.email = email;
              removeButton.addEventListener("click", handleUnregister);
              listItem.appendChild(removeButton);
            }

            participantsListElement.appendChild(listItem);
          });

          participantsSection.appendChild(participantsListElement);
          participantsContainer.appendChild(participantsSection);
        } else {
          addText(participantsContainer, "p", "No participants yet");
        }
        activityCard.appendChild(participantsContainer);
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.textContent =
        "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (response.status === 401) {
        await refreshAuthState();
        displayMessage(
          signupMessage,
          "Your teacher session expired. Please sign in again.",
          "error"
        );
      } else if (response.ok) {
        displayMessage(signupMessage, result.message, "success");
        await fetchActivities();
      } else {
        displayMessage(
          signupMessage,
          result.detail || "An error occurred.",
          "error"
        );
      }
    } catch (error) {
      displayMessage(
        signupMessage,
        "Failed to unregister. Please try again.",
        "error"
      );
      console.error("Error unregistering:", error);
    }
  }

  accountButton.addEventListener("click", () => {
    const isOpen = !accountMenu.hidden;
    accountMenu.hidden = isOpen;
    accountMenu.classList.toggle("hidden", isOpen);
    accountButton.setAttribute("aria-expanded", String(!isOpen));
  });

  loginOpenButton.addEventListener("click", () => {
    accountMenu.hidden = true;
    accountMenu.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
    loginError.textContent = "";
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("login-cancel").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.textContent = "";
    loginError.classList.add("hidden");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        loginError.textContent = result.detail || "Unable to sign in.";
        loginError.classList.remove("hidden");
        return;
      }

      isTeacher = true;
      currentUsername = result.username;
      updateAuthUI();
      loginDialog.close();
      loginForm.reset();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Unable to sign in. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Sign-out request failed.");
      }
      isTeacher = false;
      currentUsername = null;
      accountMenu.hidden = true;
      accountMenu.classList.add("hidden");
      accountButton.setAttribute("aria-expanded", "false");
      updateAuthUI();
      await fetchActivities();
    } catch (error) {
      displayMessage(signupMessage, "Unable to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!isTeacher) {
      return;
    }

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (response.status === 401) {
        await refreshAuthState();
        displayMessage(
          signupMessage,
          "Your teacher session expired. Please sign in again.",
          "error"
        );
      } else if (response.ok) {
        displayMessage(signupMessage, result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        displayMessage(
          signupMessage,
          result.detail || "An error occurred.",
          "error"
        );
      }
    } catch (error) {
      displayMessage(
        signupMessage,
        "Failed to sign up. Please try again.",
        "error"
      );
      console.error("Error signing up:", error);
    }
  });

  async function initialize() {
    try {
      await refreshAuthState();
    } catch (error) {
      console.error("Error checking teacher session:", error);
      updateAuthUI();
    }
    await fetchActivities();
  }

  initialize();
});
