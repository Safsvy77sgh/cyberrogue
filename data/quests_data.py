# data/quests_data.py

QUESTS = {
    'chapter_1': [
        {
            'id': 'quest_1_1',
            'title': 'Выбраться из лаборатории',
            'description': 'Найдите выход из разрушенного комплекса',
            'objectives': [
                {'type': 'kill', 'target': 'drone', 'count': 5, 'description': 'Уничтожьте 5 дронов'},
                {'type': 'collect', 'target': 'energy', 'count': 30, 'description': 'Соберите 30 энергии'}
            ],
            'reward': {'exp': 100, 'score': 500, 'items': ['fire_rate']}
        },
        {
            'id': 'quest_1_2',
            'title': 'Восстановить связь',
            'description': 'Найдите терминал и свяжитесь с Еленой',
            'objectives': [
                {'type': 'find', 'target': 'terminal', 'description': 'Найдите терминал'},
                {'type': 'survive', 'duration': 30, 'description': 'Выживите 30 секунд'}
            ],
            'reward': {'exp': 50, 'score': 300}
        }
    ],
    'chapter_2': [
        {
            'id': 'quest_2_1',
            'title': 'Проникнуть в сектор 7',
            'description': 'Найдите базу Кейна',
            'objectives': [
                {'type': 'kill', 'target': 'elite', 'count': 3, 'description': 'Уничтожьте 3 элитных врага'},
                {'type': 'find', 'target': 'terminal', 'description': 'Найдите терминал данных'}
            ],
            'reward': {'exp': 150, 'score': 800, 'items': ['shield']}
        }
    ],
    'chapter_3': [
        {
            'id': 'quest_3_1',
            'title': 'Уничтожить фабрику',
            'description': 'Зачистите фабрику дронов',
            'objectives': [
                {'type': 'kill', 'target': 'drone', 'count': 20, 'description': 'Уничтожьте 20 дронов'},
                {'type': 'destroy', 'target': 'conveyor', 'count': 3, 'description': 'Разрушьте 3 конвейера'}
            ],
            'reward': {'exp': 200, 'score': 1200, 'items': ['weapon_shotgun']}
        }
    ],
    'chapter_4': [
        {
            'id': 'quest_4_1',
            'title': 'Сбежать из ловушки',
            'description': 'Выберитесь из засады',
            'objectives': [
                {'type': 'survive', 'duration': 60, 'description': 'Выживите 60 секунд'},
                {'type': 'kill', 'target': 'elite', 'count': 5, 'description': 'Уничтожьте 5 элитных врагов'}
            ],
            'reward': {'exp': 250, 'score': 1500}
        }
    ],
    'chapter_5': [
        {
            'id': 'quest_5_1',
            'title': 'Проникнуть на станцию',
            'description': 'Проберитесь на орбитальную станцию',
            'objectives': [
                {'type': 'kill', 'target': 'hybrid', 'count': 10, 'description': 'Уничтожьте 10 гибридов'},
                {'type': 'find', 'target': 'kane', 'description': 'Найдите Кейна'}
            ],
            'reward': {'exp': 300, 'score': 2000, 'items': ['weapon_laser']}
        }
    ],
    'chapter_6': [
        {
            'id': 'quest_6_1',
            'title': 'Достичь ядра',
            'description': 'Проникните в ядро ГЕНЕЗИСА',
            'objectives': [
                {'type': 'kill', 'target': 'avatar', 'count': 1, 'description': 'Уничтожьте аватара ИИ'},
                {'type': 'find', 'target': 'core', 'description': 'Найдите ядро'}
            ],
            'reward': {'exp': 500, 'score': 5000}
        }
    ],
    'chapter_7': [
        {
            'id': 'quest_7_1',
            'title': 'Последний выбор',
            'description': 'Сделайте выбор, определяющий судьбу человечества',
            'objectives': [
                {'type': 'choice', 'options': ['disable_ai', 'merge_ai'], 'description': 'Сделайте выбор'}
            ],
            'reward': {'exp': 1000, 'score': 10000}
        }
    ]
}

# Ресурсы для крафтинга
CRAFTING_RECIPES = {
    'medkit': {
        'materials': {'scrap': 10, 'circuit': 2},
        'result': {'type': 'repair', 'amount': 50}
    },
    'turret': {
        'materials': {'scrap': 20, 'circuit': 5},
        'result': {'type': 'turret', 'damage': 20, 'duration': 10}
    },
    'upgrade_weapon': {
        'materials': {'scrap': 15, 'circuit': 3},
        'result': {'type': 'damage_boost', 'amount': 5}
    }
}