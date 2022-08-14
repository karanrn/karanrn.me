---
title: "GraphQL: Query filtering with relay and graphene-python"
date: 2021-03-27
tags: [graphql, python, graphene]
categories: [tech, development]
---
GraphQL is query language for API. It simplifies, isolates, and fastens the development and API releases. This post assumes the reader is aware of basics of GraphQL concepts like query, mutation, and schema. If you have stumbled here for introduction to GraphQL, please go through this [tutorial](https://graphql.org/learn/).

Most of the implementations on the web for GraphQL with python are using [Django](https://www.djangoproject.com/) which packs lot of features and plugins to ease the development with tradeoff to huge code base for simple application. I will be focusing on [Flask](https://flask.palletsprojects.com/en/1.1.x/) as it has lesser footprint and best suited for implementing small applications.

[Relay](https://relay.dev/docs/) is a GraphQL client developed by Facebook for React. It provides pagination, caching (reusing cached data) out of the box. [Graphene-Python](https://graphene-python.org/) has complete support for relay.

A simple query with filter (without relay) to fetch books basis title:
```graphql
query{
  allBooks(title:"Da Vinci Code"){
    id
    title
  }
}
````

Response from the above query:
```json
{
  "data": {
    "allBooks": [
      {
        "id": "3",
        "title": "Da Vinci Code"
      }
    ]
  }
}
```

Relay uses connections, edges, and node notation to structure/format data and requests. Connections is a collection of objects containing information about edges, nodes, page, cursor, and other metadata of the page. Edges are collections of records, it helps in pagination and node is the actual record/data. More about Relay connections, edges, and node can be read [here](https://relay.dev/graphql/connections.htm).

I could not find easier implementation of relay with filtering using flask and graphene-python. For application to use relay, we need to add relay node to the schema for querying or mutation.

Relay can be enabled or implemented as below:
```python
class BookObject(SQLAlchemyObjectType):
    class Meta:
        model = Book
        interfaces = (graphene.relay.Node, )
 
class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()
    all_books = SQLAlchemyConnectionField(BookObject.connection)
```

A sample query making use of relay:
```graphql
query{
  allBooks{
    edges{
      node{
        id
        title
      }
    }
  }
}
```
A response for the above query:
```json
{
  "data": {
    "allBooks": {
      "edges": [
        {
          "node": {
            "id": "Qm9va09iamVjdDoz",
            "title": "Da Vinci Code"
          }
        },
        {
          "node": {
            "id": "Qm9va09iamVjdDo1",
            "title": "TensorFlow"
          }
        },
        {
          "node": {
            "id": "Qm9va09iamVjdDo2",
            "title": "Deception point"
          }
        }
      ]
    }
  }
}
```

So to enable or implement filtering the query with relay can be by sub-classing SQLAlchemyConnectionField class of graphene_sqlalchemy in graphene-python. We need to implement get_query method of the SQLAlchemyConnectionField to filter on the attributes/columns of the model.

Code for the same:
```python
class MyConnectionField(SQLAlchemyConnectionField):
    # Below attributes/fields are for pagination and implemented by relay 
    RELAY_ARGS = ['first', 'last', 'before', 'after']
 
    @classmethod
    def get_query(cls, model, info, **args):
        query = super(MyConnectionField, cls).get_query(model, info, **args)
        for field, value in args.items():
            if field not in cls.RELAY_ARGS:
                query = query.filter(getattr(model, field) == value)
        return query
```

And now we can pass fields to be used for query filtering as part of our SQLAlchemyConnectionField:
```python
class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()
    all_books = MyConnectionField(BookObject,
    title = graphene.String(),
    year = graphene.Int())
```

Now, we can query with filters using relay:
```graphql
query{
  allBooks(title:"Da Vinci Code"){
    edges{
      node{
        id
        title
      }
    }
  }
}
```

And response for the above query:
```json
{
  "data": {
    "allBooks": {
      "edges": [
        {
          "node": {
            "id": "Qm9va09iamVjdDoy",
            "title": "Da Vinci Code"
          }
        }
      ]
    }
  }
}
```

For complete implementation of GraphQL in python using Flask, Graphene-Python, and SQLAlchemy, you can check the code on my [GitHub](https://github.com/karanrn/graphql-python).

---
### References
1. [Introduction to GraphQL](https://www.howtographql.com/basics/0-introduction/)

2. [Github GraphQL API](https://docs.github.com/en/graphql/guides/introduction-to-graphql#discovering-the-graphql-api)

3. [GraphQL Schema Definition Language](https://www.prisma.io/blog/graphql-sdl-schema-definition-language-6755bcb9ce51)

4. [GraphQL-Flask](https://jeffersonheard.github.io/python/graphql/2018/12/08/graphene-python.html)

5. [SQLAlchemy instead of Flask-SQLAlchemy](https://towardsdatascience.com/use-flask-and-sqlalchemy-not-flask-sqlalchemy-5a64fafe22a4)

6. [Graphene-Python](https://docs.graphene-python.org/en/latest/)

7. [How to use Fields, Fragments, and more](https://betterprogramming.pub/graphql-tutorial-how-to-use-fields-fragments-and-more-ec478896ede7)