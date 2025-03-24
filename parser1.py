import requests
import time
import json
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass, asdict

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("vacancies.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Data structure for a vacancy
@dataclass
class Vacancy:
    title: str
    company: str
    salary: Optional[Dict[str, str]]
    url: str
    description: str
    skills: List[str]

class HHruParser:
    BASE_URL = "https://api.hh.ru/vacancies"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    def __init__(self, search_query: str = "Python developer", max_pages: int = 3):
        self.search_query = search_query
        self.max_pages = max_pages
        self.found_vacancies: List[Vacancy] = []

    def fetch_vacancies(self) -> None:
        """Main method to fetch vacancies from hh.ru"""
        for page in range(self.max_pages):
            try:
                params = {
                    "text": self.search_query,
                    "page": page,
                    "per_page": 50,
                    "area": 1,  # Moscow
                }
                response = requests.get(self.BASE_URL, headers=self.HEADERS, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data.get("items"):
                    logger.warning(f"No vacancies found on page {page}.")
                    break

                logger.info(f"Processing page {page + 1}/{self.max_pages}...")
                self._process_vacancies(data["items"])
                time.sleep(1)  # Delay between requests

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                break

    def _process_vacancies(self, vacancies_data: List[Dict]) -> None:
        """Process raw vacancy data"""
        for vacancy_data in vacancies_data:
            try:
                full_info = requests.get(
                    f"{self.BASE_URL}/{vacancy_data['id']}",
                    headers=self.HEADERS,
                    timeout=5,
                ).json()

                skills = [skill["name"] for skill in full_info.get("key_skills", [])]
                salary = self._parse_salary(vacancy_data.get("salary"))

                vacancy = Vacancy(
                    title=vacancy_data["name"],
                    company=vacancy_data["employer"]["name"],
                    salary=salary,
                    url=vacancy_data["alternate_url"],
                    description=full_info.get("description", ""),
                    skills=skills,
                )
                self.found_vacancies.append(vacancy)

            except Exception as e:
                logger.error(f"Error processing vacancy {vacancy_data.get('id')}: {e}")

    @staticmethod
    def _parse_salary(salary_data: Optional[Dict]) -> Optional[Dict[str, str]]:
        """Format salary data"""
        if not salary_data:
            return None
        return {
            "from": salary_data.get("from"),
            "to": salary_data.get("to"),
            "currency": salary_data.get("currency"),
            "gross": salary_data.get("gross"),
        }

    def save_to_json(self, filename: str = "vacancies.json") -> None:
        """Save results to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(vacancy) for vacancy in self.found_vacancies],
                f,
                ensure_ascii=False,
                indent=4,
            )
        logger.info(f"Data saved to {filename}")

if __name__ == "__main__":
    parser = HHruParser(search_query="Python developer", max_pages=2)
    parser.fetch_vacancies()
    parser.save_to_json()

    # Print stats
    print(f"\nFound vacancies: {len(parser.found_vacancies)}")
    if parser.found_vacancies:
        print("Example vacancy:")
        print(f"Title: {parser.found_vacancies[0].title}")
        print(f"Company: {parser.found_vacancies[0].company}")
        print(f"Salary: {parser.found_vacancies[0].salary}")
        print(f"URL: {parser.found_vacancies[0].url}")
