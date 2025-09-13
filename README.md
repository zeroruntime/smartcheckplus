# SmartCheckPlus

## Project Overview

This repository contains the code for SmartCheckPlus, a project focusing on lab access management and security. The system leverages QR code scanning and user profiles to track lab sessions and manage user access.

## Key Features & Benefits

- **QR Code Scanning:** Facilitates quick and secure access to lab facilities.
- **User Management:** Supports different user types (Administrators, Lab Supervisors, Regular Students, Temporary Students, Guests).
- **Access Logging:** Tracks user access and lab session details for security and auditing purposes.
- **Lab Session Management:** Enables supervisors to manage and monitor lab sessions.
- **Customizable System Settings:** Allows administrators to configure system-wide parameters.

## Prerequisites & Dependencies

Before setting up the project, ensure you have the following installed:

- **Python:** (version 3.x recommended)
- **Node.js:** (version 16 or higher)
- **pip:** (Python package installer)
- **npm:** (Node Package Manager)

The project relies on the following Python packages:

- Django
- qrcode
- django-environ
- Tailwind 4

The project uses the following Javascript packages:

- gulp

## Installation & Setup Instructions

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/zeroruntime/smartcheckplus/
    cd smartcheckplus
    ```

2.  **Set up Python Virtual Environment (Recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```

3.  **Install Python Dependencies:**

    ```bash
    pip install -r requirements.txt # Create a requirements.txt file first!
    ```
   (You will need to create a `requirements.txt` file that includes all dependencies)

   Example `requirements.txt`:
    ```
    Django==4.2.1
    qrcode==7.4.2
    django-environ==0.11.2
    Pillow==10.2.0
    ```

4.  **Apply Migrations:**

    ```bash
    python manage.py migrate
    ```

5.  **Create Superuser:**

    ```bash
    python manage.py createsuperuser
    ```

6.  **Install Node.js Dependencies:**

    ```bash
    npm install
    ```

7.  **Run Gulp (Optional):**

    ```bash
    gulp
    ```

8.  **Start the Django Development Server:**

    ```bash
    python manage.py runserver
    ```

## Usage Examples & API Documentation

#### Accessing the Admin Interface

-   After creating a superuser, access the Django admin interface at `http://127.0.0.1:8000/admin/`.
-   Log in with your superuser credentials to manage UserProfiles, Students, Lab Sessions, and System Settings.


## Configuration Options

The project's behavior can be configured through the Django settings file (`smartcheckplus/settings.py`) and system settings managed within the Django admin interface.

-   **Database Settings:** Configure the database connection in `smartcheckplus/settings.py`.

    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',  # Or your preferred database
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    ```

-   **System Settings:** Use the admin interface to configure parameters like lab session duration.

## Contributing Guidelines

We welcome contributions to SmartCheckPlus! To contribute:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Implement your changes, adhering to the coding style and guidelines.
4.  Write tests to cover your changes.
5.  Submit a pull request with a clear description of your changes.

## License Information

This project does not specify a license, so all rights are reserved.

## Acknowledgments

We acknowledge the use of Django, qrcode, django-environ and other open-source libraries that have contributed to the development of this project.
